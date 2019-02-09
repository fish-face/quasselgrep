from __future__ import print_function
from __future__ import absolute_import
from builtins import range
from builtins import object
from . import output
from .msgtypes import *

from time import time
from datetime import datetime
import re
from threading import Thread

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')
MSG_NORMAL = 1
MSG_ACTION = 4

class Param(object):
	"""Holds information about a parameter that can be searched on"""
	def __init__(self, name, clause, morenames=[]):
		self.names = [name] + morenames
		self.clause = clause


class TypesParam(Param):
	def __init__(self, msg_types):
		self.names = []
		self.clause = 'backlog.type IN %s' % (msg_types,)


class Query(object):
	"""Represents a single query to the database"""
	joins = [
		"JOIN sender ON sender.senderid = backlog.senderid",
		"JOIN buffer ON buffer.bufferid = backlog.bufferid",
		"JOIN network ON network.networkid = buffer.networkid",
		"JOIN quasseluser ON network.userid = quasseluser.userid"
	]

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
		if options.ignorecase:
			textParam = Param('text', 'LOWER(backlog.message) LIKE LOWER(%(param)s)')
		else:
			textParam = Param('text', 'backlog.message LIKE %(param)s')

		self.params = {
				'text' : textParam,
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
			lags = ['       LAG(backlog.messageid, %d) OVER ctxt_window AS ctxt_id_%d,' % (i, i) for i in range(1, ctxt+1)]
			leads = ['       LEAD(backlog.messageid, %d) OVER ctxt_window AS ctxt_id_%d,' % (i, ctxt+i) for i in range(1, ctxt+1)]
			leads[-1] = leads[-1][:-1]
			return lags + leads
		else:
			return ''

	def columns(self):
		columns = []
		if self.options.db_type == 'postgres':
			columns.append('backlog.time::timestamp(0)')
		elif self.options.db_type == 'sqlite':
			columns.append("datetime(backlog.time, 'unixepoch') as time")
		columns += ["backlog.type", "backlog.message", "sender.sender", "buffer.buffername", "network.networkname"]

		return columns

	def basequery(self, only_ids=False, context=False):
		"""Common start to queries

		If only_ids is specified, only request IDs, not full records."""
		query = ["SELECT backlog.messageid"]

		columns = [''] + self.columns()

		if not only_ids:
			query[0] = query[0] + ',\n       '.join(columns)

		if context:
			query[-1] += ','
			query += self.contextbits()

		query += ["FROM backlog"] + self.joins

		return query

	def search_query(self, only_ids=False):
		"""Normal query"""
		params = self.filter_params(list(self.params.keys()))
		query = self.basequery(only_ids)
		query.append(self.where_clause(params))

		if self.limit:
			query.insert(0,"SELECT * FROM (")
			query.append("ORDER BY backlog.time DESC")
			query.append("LIMIT ?) AS query")
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

	def context_query(self):
		params = self.filter_params(["user", "network", "buffer", "fromtime", "totime"])
		ctxt_query = self.basequery(only_ids=True, context=True)
		central_id_query, all_params = self.search_query(only_ids=True)
		central_id_query = central_id_query.replace('\n', '\n    ')

		# First set up two WITH queries. The first is getting the IDs of the results from the actual search;
		# the second running a looser query (it ignores the message search part for example), getting not just
		# matching IDs but IDs of the next/previous N rows that also match the loose query in the same buffer.
		context_extra_queries = [
			'WITH central_ids AS (',
			'    ' + central_id_query + '),',
			'context_ids AS (',
			'    ' + '\n    '.join(ctxt_query),
			'    ' + self.where_clause(params),
			'    WINDOW ctxt_window AS (PARTITION BY backlog.bufferid ORDER BY backlog.time, backlog.messageid ASC)',
			'    ORDER BY time'
			')']

		# Extract the IDs and annotate the rows with ctxt_for, the ID of the row which 'caused' that this one to match.
		context_unions = [
			['    UNION',
			 '    SELECT ctxt_id_%d AS ctxt_for, messageid FROM context_ids' % (i),
			 '    WHERE context_ids.ctxt_id_%d IN (SELECT * FROM central_ids)' % (i)]
			for i in range(1, self.options.context*2 + 1)
		]

		columns = ['backlog.messageid'] + self.columns() + ['context.ctxt_for']

		# This is the *actual* query.
		context_query = [
			'SELECT ' + ', '.join(columns),
			'FROM (',
			'    SELECT messageid AS ctxt_for, messageid FROM context_ids',
			'    WHERE context_ids.messageid IN (SELECT * FROM central_ids)']
		context_query += [l for u in context_unions for l in u] + [
			') context',
			'JOIN backlog ON context.messageid = backlog.messageid'] + self.joins
		context_query += ['ORDER BY ctxt_for, time']

		return ('\n'.join(context_extra_queries + context_query), all_params + [getattr(self,param) for param in params])


	def run(self):
		"""Run a database query according to options

		Runs a database query according the options specified in
		options using the supplied cursor object."""

		start = time()

		# If the user wants context lines we have to use a different query
		if self.options.context:
			query, params = self.context_query()
			if self.options.debug:
				print("Getting context of IDs with:")
				print(query)
				print(params)
				query = 'EXPLAIN ' + query
			self.execute_query(query, params)
		else:
			# Simple case
			if not self.options.debug:
				self.execute_query(*self.search_query())
			else:
				query, params = self.search_query()
				print(query)
				print(params)
				self.cursor.execute("EXPLAIN " + query, params)

		print("Query completed in %.2f seconds" % (time() - start))
		return self.formatter(self.cursor)

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

	def formatter(self, results):
		"""Iterable returning formatted database rows

		Take an iterable of rows as returned from the database and format them like a line from IRC."""
		context = self.options.context
		ctxt_for = None
		messageid_history = []

		for result in results:
			# Special handling for output of context
			if context:
				messageid = result[0]

				# There may be duplicate rows where the context of one message is also context of another. So if we see
				# the same msg id, skip it.
				if messageid in messageid_history:
					ctxt_for = result[7]
					continue
				# When ctxt_for changes we are changing context groups: print a separator. At this point we also clear
				# the history of ids. It could be that the previous group was from buffer A, we are now printing a
				# group from buffer B and we will see duplicate rows from buffer A again - but we still want to print
				# them because there was stuff in the way, so erasing the history is fine.
				if ctxt_for and ctxt_for != result[7]:
					messageid_history = []
					yield '---'
				messageid_history.append(messageid)
				ctxt_for = result[7]

			#Extract data we care about
			time = result[1]
			type = result[2]
			message = result[3]
			try:
				sender = maskre.match(result[4]).group('nick')
			except:
				sender = result[4]
			buffer = result[5] if not self.buffer else None

			yield output.format(time, type, message, sender, buffer)

