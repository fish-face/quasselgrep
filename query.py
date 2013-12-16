from time import time
from datetime import datetime
import re

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')
MSG_NORMAL = 1
MSG_ACTION = 4

class Query:
	params = {
		'text' : 'backlog.message',
		'user' : 'quasseluser.username',
		'network' : 'network.networkname',
		'buffer' : 'buffer.buffername',
		'sender' : 'sender.sender',
	}
	def __init__(self, text, user, network='', buffer='', sender='', timerange=None):
		self.text = text
		self.user = user

		self.network = network
		self.buffer = buffer
		self.sender = sender

		self.timerange = timerange
		if timerange:
			self.fromtime = timerange[0]
			self.totime = timerange[1]

	def match_expression(self, param, param_string):
		if param == 'text':
			return "%s LIKE %s" % (self.params[param], param_string), self.text
		elif param == 'user':
			return "%s in(%s)" % (self.params[param], param_string), self.user_list
		elif param == 'network':
			return " in(%s)" % (2)

	def where_clause(self, params, db_type):
		if db_type == 'postgres':
			param_string = '%s'
		elif db_type == 'sqlite':
			param_string = '?'

		if not params:
			return ''

		clause = 'WHERE '
		ands = ['%s LIKE %s' % (self.params[param], param_string) for param in params]
		if self.timerange:
			if db_type == 'sqlite':
				self.fromtime = self.fromtime.strftime('%s')
				self.totime = self.totime.strftime('%s')
			ands.append('backlog.time > %s' % param_string)
			ands.append('backlog.time < %s' % param_string)
			params.append('fromtime')
			params.append('totime')
		clause += ' AND '.join(ands)
		return clause

	def basequery(self, db_type, only_ids=False):
		query = ["SELECT backlog.messageid" + (',' if not only_ids else '')]

		if not only_ids:
			if db_type == 'postgres':
				query.append("       backlog.time::timestamp(0),")
			elif db_type == 'sqlite':
				query.append("       datetime(backlog.time, 'unixepoch'),")
			query += ["       backlog.type, backlog.message,",
					  "       sender.sender, buffer.buffername, network.networkname"]

		query += ["FROM backlog",
		          "JOIN sender ON sender.senderid = backlog.senderid",
		          "JOIN buffer ON buffer.bufferid = backlog.bufferid",
		          "JOIN network ON network.networkid = buffer.networkid",
		          "JOIN quasseluser ON network.userid = quasseluser.userid"]

		return query

	def search_query(self, db_type, only_ids=False):
		params = [param for param in self.params.keys() if getattr(self,param)]
		query = self.basequery(db_type, only_ids)
		query.append(self.where_clause(params, db_type))

		query.append("ORDER BY backlog.time")
		return ('\n'.join(query), [getattr(self,param) for param in params])

	def allpossible_query(self, db_type):
		params = filter(lambda x: getattr(self,x), ["user", "network", "buffer"])
		query = self.basequery(db_type, only_ids=True)
		query.append(self.where_clause(params, db_type))

		query.append("ORDER BY backlog.time")
		return ('\n'.join(query), [getattr(self,param) for param in params])

	def get_rows_with_ids(self, ids, db_type):
		query = self.basequery(db_type)
		query.append("WHERE backlog.messageid IN %s")
		query.append("ORDER BY backlog.time")

		return ('\n'.join(query), (tuple(ids),))


	def run(self, cursor, options):
		start = time()
		if options.context:
			cursor.execute(*self.allpossible_query(options.db_type))
			allids = [res[0] for res in cursor.fetchall()]
			cursor.execute(*self.search_query(options.db_type, only_ids=True))

			context = int(options.context)
			results = []
			for result in cursor:
				idx = allids.index(result[0])
				results += allids[idx-context:idx+context+1]

			cursor.execute(*self.get_rows_with_ids(results, options.db_type))
		else:
			cursor.execute(*self.search_query(options.db_type))

		print "Query completed in %.2f seconds" % (time() - start)
		return cursor.fetchall()

	def format(self, result):
		time = result[1]
		type = result[2]
		message = result[3]
		try:
			sender = maskre.match(result[4]).group('nick')
		except:
			sender = result[4]
		buffer = result[5]

		formatted = '[%s] ' % time

		if type == MSG_NORMAL:
			if not self.buffer and buffer:
				formatted += '<%s/%s> ' % (sender, buffer)
			else:
				formatted += '<%s> ' % (sender)
		else:
			if not self.buffer and buffer:
				formatted += '%s: * %s ' % (buffer, sender)
			else:
				formatted += '* %s ' % (sender)


		formatted += message

		return formatted

