from datetime import datetime
import re

maskre = re.compile('(?P<nick>.*)!(.*)@(.*)')

class Query:
	def __init__(self, text, user, network='', buffer='', sender=''):
		self.text = text
		self.user = user if user else '%'

		self.network = network if network else '%'
		self.buffer = buffer if buffer else '%'
		self.sender = sender if sender else '%'

	def querystring(self):
		#return """SELECT backlog.time, backlog.message,
        #                 sender.sender, buffer.buffername, network.networkname
        #          FROM backlog
        #          JOIN sender ON sender.senderid = backlog.senderid
        #          JOIN buffer ON buffer.bufferid = backlog.bufferid
        #          JOIN network ON network.networkid = buffer.networkid
        #          JOIN quasseluser ON network.userid = quasseluser.userid
        #          WHERE backlog.message LIKE ? """, (self.text,)
		return """SELECT backlog.time, backlog.message,
                         sender.sender, buffer.buffername, network.networkname
                  FROM backlog
                  JOIN sender ON sender.senderid = backlog.senderid
                  JOIN buffer ON buffer.bufferid = backlog.bufferid
                  JOIN network ON network.networkid = buffer.networkid
                  JOIN quasseluser ON network.userid = quasseluser.userid
                  WHERE backlog.message LIKE %s AND
                        sender.sender LIKE %s AND
                        network.networkname LIKE %s AND
                        buffer.buffername LIKE %s AND
                        quasseluser.username LIKE %s
                  ORDER BY backlog.time""", (self.text, self.sender, self.network, self.buffer, self.user)

	def run(self, cursor, options):
		querystring, params = self.querystring()
		if options.db_type == 'sqlite':
			querystring = querystring.replace('%s', '?')

		cursor.execute(querystring, params)
		return cursor.fetchall()

	def format(self, result):
		if isinstance(result[0], int):
			timestamp = datetime.fromtimestamp(result[0]).strftime('%Y-%m-%d %H:%M:%S')
		else:
			timestamp = result[0]

		try:
			sender = maskre.match(result[2]).group('nick')
		except:
			sender = result[2]

		if '%' in self.buffer[0] and result[3]:
			return '[%s] <%s/%s> %s' % (timestamp, result[3], sender, result[1])
		else:
			return '[%s] <%s> %s' % (timestamp, sender, result[1])

