
from builtins import object
class Db(object):
	def __init__(self):
		pass

	def connect(self, options):
		if options.db_type == 'sqlite':
			options.param_string = '?'
			try:
				import sqlite3 as dbmodule
			except ImportError:
				raise ValueError('Cannot open an sqlite database without sqlite3 python module')

			self.connection = dbmodule.connect(options.db_name, check_same_thread=False)
			cursor = self.connection.cursor()

			#Newer sqlite versions have timestamps in milliseconds.
			cursor.execute('SELECT value FROM coreinfo WHERE key="schemaversion"')
			results = cursor.fetchall()
			if len(results) != 1:
				raise ValueError('Incorrect sqlite schemaversion format')
			options.sqlite_version = results[0][0]
		elif options.db_type == 'postgres':
			options.param_string = '%s'
			try:
				import psycopg2 as dbmodule
			except ImportError:
				raise ValueError('Cannot connect to a postgres database without psycopg2 installed')

			self.connection = dbmodule.connect(database=options.db_name,
			                                   user=options.db_user,
			                                   password=options.db_password,
			                                   host=options.db_host)
			try:
				self.connection.set_session(readonly=True)
			except AttributeError:
				pass
			cursor = self.connection.cursor(name='quasselgrep')
		else:
			raise ValueError('Invalid database type: %s' % (options.db_type))

		return cursor
