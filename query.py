import output

from time import time
from datetime import datetime
import re

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')
MSG_NORMAL = 1
MSG_ACTION = 4

class Query:
	"""Represents a single query to the database"""
	params = {
		'text' : 'backlog.message',
		'user' : 'quasseluser.username',
		'network' : 'network.networkname',
		'buffer' : 'buffer.buffername',
		'sender' : 'sender.sender',
	}
	def __init__(self, cursor, options, text, user, network='', buffer='', sender='', timerange=None):
		self.cursor = cursor
		self.options = options

		self.text = text
		self.user = user

		self.network = network
		self.buffer = buffer
		self.sender = sender

		self.timerange = timerange
		if timerange:
			self.fromtime = timerange[0]
			self.totime = timerange[1]

	#def match_expression(self, param, param_string):
	#	if param == 'text':
	#		return "%s LIKE %s" % (self.params[param], param_string), self.text
	#	elif param == 'user':
	#		return "%s in(%s)" % (self.params[param], param_string), self.user_list
	#	elif param == 'network':
	#		return " in(%s)" % (2)

	def where_clause(self, params):
		"""Build a where clause based on specified params"""
		if self.options.db_type == 'postgres':
			param_string = '%s'
		elif self.options.db_type == 'sqlite':
			param_string = '?'

		if not params:
			return ''

		clause = 'WHERE '
		#Conjunction of LIKEs.
		#TODO Consider changing this to equality for buffer, sender.
		ands = ['%s LIKE %s' % (self.params[param], param_string) for param in params]
		if self.timerange:
			if self.options.db_type == 'sqlite':
				self.fromtime = self.fromtime.strftime('%s')
				self.totime = self.totime.strftime('%s')
			ands.append('backlog.time > %s' % param_string)
			ands.append('backlog.time < %s' % param_string)
			params.append('fromtime')
			params.append('totime')
		clause += ' AND '.join(ands)
		return clause

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
		params = [param for param in self.params.keys() if getattr(self,param)]
		query = self.basequery(only_ids)
		query.append(self.where_clause(params))

		query.append("ORDER BY backlog.time")
		return ('\n'.join(query), [getattr(self,param) for param in params])

	def allpossible_query(self):
		"""Get all possible IDs - ignore text and sender"""
		params = filter(lambda x: getattr(self,x), ["user", "network", "buffer"])
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
			self.cursor.execute(*self.allpossible_query())
			allids = [res[0] for res in self.cursor.fetchall()]

			#Then run the actual search, retrieving only the IDs
			self.cursor.execute(*self.search_query(only_ids=True))

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
			self.cursor.execute(*self.get_rows_with_ids(ids))

			#Finally insert the separators
			results = self.cursor.fetchall()
			for gap_index in gaps:
				results.insert(gap_index, None)
		else:
			#Simple case
			print "Executing"
			self.cursor.execute(*self.search_query())
			print "Executed"
			results = self.cursor.fetchall()
			#results = [['wat','wat',1,'wat','wat','wat','wat','wat']]

		print "Query completed in %.2f seconds" % (time() - start)
		return results

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

