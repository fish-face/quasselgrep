from __future__ import absolute_import
from __future__ import print_function
from . import output
from .msgtypes import *

from time import time
from datetime import datetime
import re
from threading import Thread
from six.moves import range

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')
MSG_NORMAL = 1
MSG_ACTION = 4

class Param:
	"""Holds information about a parameter that can be searched on"""
	def __init__(self, name, clause, morenames=[]):
		self.names = [name] + morenames
		self.clause = clause


class TypesParam(Param):
	def __init__(self, msg_types):
		self.names = []
		self.clause = 'backlog.type IN %s' % (msg_types,)


class ContextGroup(object):
	def __init__(self, row, ctxt_for_col, ctxt):
		self.ctxt_for_col = ctxt_for_col
		self.ctxt = ctxt

		self.rows = [None]
		self.buff = row[5]
		self.first_for = row[ctxt_for_col]

		self.got_pre_rows = -1
		self.got_post_rows = 0
		self.post = False

		self.add_row(row)

	def matches_row(self, row):
		return row[5] == self.buff and row[self.ctxt_for_col] == self.ctxt_for

	def add_row(self, row):
		self.rows.append(row)
		self.ctxt_for = row[self.ctxt_for_col]

		# Track whether we have enough rows before and after
		if self.post:
			self.got_post_rows += 1
		else:
			self.got_pre_rows += 1

		if row[0] == row[self.ctxt_for_col]:
			self.got_post_rows = 0
			self.post = True

	def add_group(self, other):
		self.rows += other.rows[1:]
		other.rows = []

	def pre_finished(self):
		return self.got_pre_rows >= self.ctxt

	def finished(self):
		return self.got_post_rows >= self.ctxt


class Query:
	"""Represents a single query to the database"""

	def __init__(self, cursor, options, text, timerange=None):
		self.cursor = cursor
		self.options = options

		self.text = text
		self.user = options.username

		self.network = options.network
		self.buffer = options.buffer
		self.sender = options.sender
		if options.sender:
			self.sender_pattern = options.sender + '!%'

		self.timerange = timerange
		if timerange:
			if options.db_type == 'postgres':
				self.fromtime = timerange[0]
				self.totime = timerange[1]
			elif options.db_type == 'sqlite':
				self.fromtime = timerange[0].strftime('%s')
				self.totime = timerange[1].strftime('%s')

		if options.inclusive:
			self.msg_types = (MSG, NOTICE, ACTION, NICK, MODE, JOIN, PART, QUIT, KICK, TOPIC, INVITE, SPLITJOIN, SPLITQUIT)
		else:
			self.msg_types = (MSG, NOTICE, ACTION)

		if options.limit:
			self.limit = int(options.limit)
		else:
			self.limit = 0

		#TODO Consider changing this to equality for buffer
		self.params = {
			'text' : Param('text', 'backlog.message LIKE %(param)s'),
			'user' : Param('user', 'quasseluser.username = %(param)s'),
			'network' : Param('network', 'network.networkname LIKE %(param)s'),
			'buffer' : Param('buffer', 'buffer.buffername LIKE %(param)s'),
			'sender' : Param('sender', '(sender.sender = %(param)s OR sender.sender LIKE %(param)s)', ['sender_pattern']),
			'fromtime' : Param('fromtime', 'backlog.time > %(param)s'),
			'totime' : Param('totime', 'backlog.time < %(param)s'),
			# SQLite can't handle tuple parameters, and they're not from user
			# input so just include them directly in the string
			'msg_types' : TypesParam(self.msg_types),
		}

	#def get_senders(self, sender):
	#	"""Find matching user ids"""

	#	if not sender:
	#		return None

	#	sender_pattern = '%s!%%' % (sender)
	#	self.cursor.execute('SELECT senderid FROM sender WHERE sender LIKE %s OR sender=%s'.replace('%s',self.options.param_string), (sender_pattern, sender))
	#	results = self.cursor.fetchall()
	#	if not results:
	#		raise ValueError('No nicks matched %s' % sender)
	#	return tuple([result[0] for result in results])

	def filter_params(self, params):
		"""return only those params which have been set"""

		return [param for param in params if getattr(self,param,None)]

	def where_clause(self, params):
		"""Build a where clause based on specified params"""
		if not params:
			return ''

		ands = []
		modified_params = []
		for param in params:
			ands.append(self.params[param].clause % {'param' : self.options.param_string})
			modified_params += self.params[param].names

		#May need to add more parameters (sender_pattern)
		params[:] = modified_params

		return 'WHERE ' + ' AND '.join(ands)

	def contextbits(self):
		if self.options.context:
			ctxt = self.options.context
			lags = ['       LAG(backlog.messageid, %d) OVER ctxt_window AS id_%d,' % (i, i) for i in range(1, ctxt+1)]
			leads = ['       LEAD(backlog.messageid, %d) OVER ctxt_window AS id_%d,' % (i, ctxt+i) for i in range(1, ctxt+1)]
			leads[-1] = leads[-1][:-1]
			return lags + leads
		else:
			return ''

	def basequery(self, only_ids=False):
		"""Common start to queries

		If only_ids is specified, only request IDs, not full records."""
		query = ["SELECT backlog.messageid, " + ('' if not only_ids else 'buffer.buffername ')]

		if not only_ids:
			if self.options.db_type == 'postgres':
				query.append("       backlog.time::timestamp(0),")
			elif self.options.db_type == 'sqlite':
				query.append("       datetime(backlog.time, 'unixepoch'),")
			query += ["       backlog.type, backlog.message,",
					  "       sender.sender, buffer.buffername, network.networkname"
			 + (',' if self.options.context else '')]
			query += self.contextbits()

		query += ["FROM backlog",
		          "JOIN sender ON sender.senderid = backlog.senderid",
		          "JOIN buffer ON buffer.bufferid = backlog.bufferid",
		          "JOIN network ON network.networkid = buffer.networkid",
		          "JOIN quasseluser ON network.userid = quasseluser.userid"]

		return query

	def search_query(self, only_ids=False):
		"""Normal query"""
		params = self.filter_params(list(self.params.keys()))
		query = self.basequery(only_ids)
		query.append(self.where_clause(params))

		if self.limit:
			query.insert(0,"SELECT * FROM (")
			query.append("ORDER BY backlog.time DESC")
			query.append("LIMIT %s) AS query")
			query.append("ORDER BY query.time")
			params.append("limit")
		else:
			query.append("ORDER BY backlog.time")
		#print '\n'.join(query)
		return ('\n'.join(query), [getattr(self,param) for param in params])

	def allpossible_query(self):
		"""Get all possible IDs - ignore text and sender"""
		params = self.filter_params(["user", "network", "buffer", "fromtime", "totime"])
		query = self.basequery(only_ids=True)
		query.append(self.where_clause(params))

		query.append("ORDER BY backlog.time")

		return ('\n'.join(query), [getattr(self,param) for param in params])

	def context_query(self, ids):
		params = self.filter_params(["user", "network", "buffer", "fromtime", "totime"])
		query = self.basequery()

		# Add a column which indicates which message id each row is context for
		# This is kind of ugly and might be better done in python
		context_for = '(CASE True WHEN messageid in %s THEN messageid ' + ' '.join(['WHEN id_%d in %%s THEN id_%d' % (i+1, i+1) for i in range(self.options.context*2)]) + ' END) as context_for'
		formats = tuple([tuple(ids)] * ((self.options.context*2) + 1))
		context_for = context_for % formats

		query.insert(0, 'SELECT *, %s FROM (' % context_for)
		query.append(self.where_clause(params))
		query += ["WINDOW ctxt_window AS (PARTITION BY backlog.bufferid ORDER BY backlog.time, backlog.messageid ASC)"]
		query.append("ORDER BY backlog.time")
		query.append(') x')

		ors = ['messageid IN %s' % (tuple(ids),)]
		ors += ['id_%d IN %s' % (i+1, tuple(ids)) for i in range(self.options.context*2)]

		query.append('WHERE (' + ' OR '.join(ors) + ')')
		query.append('ORDER BY time, messageid')

		return ('\n'.join(query), [getattr(self,param) for param in params])

	def sort_results_for_context(self, results):
		"""Sort context results for display"""
		groups = []
		group_for = {}
		ctxt = self.options.context
		ctxt_for_col = 7+ctxt*2
		# Loop over rows and group according to which row they are context for
		for row in results:
			buff = row[5]
			if buff in group_for and not group_for[buff].finished() and group_for[buff].matches_row(row):
					group_for[buff].add_row(row)
			else:
				groups.append(ContextGroup(row, ctxt_for_col, ctxt))
				group_for[buff] = groups[-1]

		# Some groups may have not enough context before the matching line; merge
		# them with a previous group
		for i, g in enumerate(groups[:-1]):
			if not g.rows:
				# Group already got squashed
				continue
			for h in groups[i+1:]:
				if h.buff != g.buff:
					continue
				if not h.pre_finished():
					# Needs more context; do merge
					g.add_group(h)
				else:
					# Don't try and merge further groups with this one
					break

		# Sort the groups according to the first row of the group which matched
		# the actual query
		groups.sort(key=lambda x:x.first_for)
		return (row for g in groups for row in g.rows)

	def run(self):
		"""Run a database query according to options

		Runs a database query according the options specified in
		options using the supplied cursor object."""

		start = time()

		#If the user wants context lines, things get complicated...
		if self.options.context:
			#First find all "possible" ids of matching rows - so ignoring
			#the search parameters apart from user, network, buffer and time.
			self.execute_query(*self.search_query(only_ids=True))
			ids = [res[0] for res in self.cursor]
			if ids:
				self.execute_query(*self.context_query(ids))
				results = self.sort_results_for_context(self.cursor.fetchall())
			else:
				results = []
		else:
			#Simple case
			if not self.options.debug:
				self.execute_query(*self.search_query())
			else:
				query, params = self.search_query()
				print(query)
				print(params)
				self.cursor.execute("EXPLAIN " + query, params)
			results = self.cursor.fetchall()

		print("Query completed in %.2f seconds" % (time() - start))
		return results

	def execute_query(self, query, params=[]):
		thread = Thread(target=self.cursor.execute, args=(query,params))
		thread.daemon = True
		thread.start()
		try:
			while True:
				thread.join(1)
				if not thread.is_alive(): break
		except KeyboardInterrupt:
			print("Stopping.")
			raise

	def format(self, result):
		"""Format a database row

		Take a list as returned from the database and format it like
		a line from IRC."""

		#Separator between contexts
		if result is None:
			return '---'

		#Extract data we care about
		time = result[1]
		type = result[2]
		message = result[3]
		try:
			sender = maskre.match(result[4]).group('nick')
		except:
			sender = result[4]
		buffer = result[5] if not self.buffer else None

		return output.format(time, type, message, sender, buffer)

