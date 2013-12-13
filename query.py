
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
                  WHERE backlog.message LIKE ? AND
                        sender.sender LIKE ? AND
                        network.networkname LIKE ? AND
                        buffer.buffername LIKE ? AND
                        quasseluser.username LIKE ?""", (self.text, self.sender, self.network, self.buffer, self.user)

	def run(self, cursor):
		print self.querystring()[1]
		cursor.execute(*self.querystring())
		return cursor.fetchall()

