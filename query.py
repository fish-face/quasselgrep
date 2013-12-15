from datetime import datetime
import re

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')

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

	def querystring(self, db_type):
		params = [param for param in self.params.keys() if getattr(self,param)]
		if db_type == 'postgres':
			query =  ["SELECT backlog.time::timestamp(0), backlog.message,"]
		elif db_type == 'sqlite':
			query =  ["SELECT datetime(backlog.time, 'unixepoch'), backlog.message,"]

		query += ["       sender.sender, buffer.buffername, network.networkname",
				  "FROM backlog",
		          "JOIN sender ON sender.senderid = backlog.senderid",
		          "JOIN buffer ON buffer.bufferid = backlog.bufferid",
		          "JOIN network ON network.networkid = buffer.networkid",
		          "JOIN quasseluser ON network.userid = quasseluser.userid"]
		query.append(self.where_clause(params, db_type))

		query.append("ORDER BY backlog.time")
		return ('\n'.join(query), [getattr(self,param) for param in params])


	def run(self, cursor, options):
		cursor.execute(*self.querystring(options.db_type))
		return cursor.fetchall()

	def format(self, result):
		try:
			sender = maskre.match(result[2]).group('nick')
		except:
			sender = result[2]

		if self.buffer and result[3]:
			return '[%s] <%s/%s> %s' % (result[0], result[3], sender, result[1])
		else:
			return '[%s] <%s> %s' % (result[0], sender, result[1])

