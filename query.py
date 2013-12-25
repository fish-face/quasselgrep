import output

from time import time
from datetime import datetime
import re
from threading import Thread

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')
MSG_NORMAL = 1
MSG_ACTION = 4

class Param:
	"""Holds information about a parameter that can be searched on"""
	def __init__(self, name, clause, morenames=[]):
		self.names = [name] + morenames
		self.clause = clause
	
class Query:
	"""Represents a single query to the database"""

	def __init__(self, cursor, options, text, user, network='', buffer='', sender='', timerange=None):
		self.cursor = cursor
		self.options = options

		self.text = text
		self.user = user

		self.network = network
		self.buffer = buffer
		self.sender = sender
		if sender:
			self.sender_pattern = sender + '!%'

		self.timerange = timerange
		if timerange:
			if options.db_type == 'postgres':
				self.fromtime = timerange[0]
				self.totime = timerange[1]
			elif options.db_type == 'sqlite':
				self.fromtime = self.fromtime.strftime('%s')
				self.totime = self.totime.strftime('%s')

		#TODO Consider changing this to equality for buffer
		self.params = {
			'text' : Param('text', 'backlog.message LIKE %(param)s'),
			'user' : Param('user', 'quasseluser.username = %(param)s'),
			'network' : Param('network', 'network.networkname LIKE %(param)s'),
			'buffer' : Param('buffer', 'buffer.buffername LIKE %(param)s'),
			'sender' : Param('sender', 'sender.sender = %(param)s OR sender.sender LIKE %(param)s', ['sender_pattern']),
			'fromtime' : Param('fromtime', 'backlog.time > %(param)s'),
			'totime' : Param('totime', 'backlog.time < %(param)s'),
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

	def basequery(self, only_ids=False):
		"""Common start to queries

		If only_ids is specified, only request IDs, not full records."""
		query = ["SELECT backlog.messageid" + (',' if not only_ids else '')]

		if not only_ids:
			if self.options.db_type == 'postgres':
				query.append("       backlog.time::timestamp(0),")
			elif self.options.db_type == 'sqlite':
				query.append("       datetime(backlog.time, 'unixepoch'),")
			query += ["       backlog.type, backlog.message,",
					  "       sender.sender, buffer.buffername, network.networkname"]

		query += ["FROM backlog",
		          "JOIN sender ON sender.senderid = backlog.senderid",
		          "JOIN buffer ON buffer.bufferid = backlog.bufferid",
		          "JOIN network ON network.networkid = buffer.networkid",
		          "JOIN quasseluser ON network.userid = quasseluser.userid"]

		return query

	def search_query(self, only_ids=False):
		"""Normal query"""
		params = self.filter_params(self.params.keys())
		query = self.basequery(only_ids)
		query.append(self.where_clause(params))

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

	def get_rows_with_ids(self, ids):
		"""Return full records of given ids"""
		query = self.basequery()
		query.append("WHERE backlog.messageid IN %s")
		query.append("ORDER BY backlog.time")

		return ('\n'.join(query), (tuple(ids),))


	def run(self):
		"""Run a database query according to options

		Runs a database query according the options specified in
		options using the supplied cursor object."""

		start = time()

		#If the user wants context lines, things get complicated...
		if self.options.context:
			#First find all "possible" ids of matching rows - so ignoring
			#the search parameters apart from user, network, buffer and time.
			self.execute_query(*self.allpossible_query())
			allids = [res[0] for res in self.cursor.fetchall()]

			#Then run the actual search, retrieving only the IDs
			self.execute_query(*self.search_query(only_ids=True))

			#Now work out the IDs of ALL records to output, including
			#the context lines
			context = int(self.options.context)
			ids = []
			gaps = [] #This will hold indices where we should insert a separator
			for result in self.cursor:
				idx = allids.index(result[0])
				to_add = allids[idx-context:idx+context+1]
				if to_add[0] not in ids and ids:
					#Add len(gaps) since results will get longer as we add
					#more separators
					gaps.append(len(ids)+len(gaps))
				ids += to_add

			#Now get full records of the computed IDs
			self.execute_query(*self.get_rows_with_ids(ids))

			#Finally insert the separators
			results = self.cursor.fetchall()
			for gap_index in gaps:
				results.insert(gap_index, None)
		else:
			#Simple case
			if not self.options.debug:
				self.execute_query(*self.search_query())
			else:
				query, params = self.search_query()
				print query
				print params
				self.cursor.execute("EXPLAIN " + query, params)
			results = self.cursor.fetchall()

		print "Query completed in %.2f seconds" % (time() - start)
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
			print "Stopping."
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

