import sqlite3

class Db:
	def __init__(self):
		pass

	def connect(self, database):
		self.connection = sqlite3.connect(database)
		return self.connection.cursor()
