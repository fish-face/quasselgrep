#!/usr/bin/env python

from __future__ import print_function
from __future__ import absolute_import

from .db import Db
from .query import Query
from . import dateparse
from .times import timespan
from . import config

import sys
from datetime import datetime
from optparse import OptionParser
from optparse import IndentedHelpFormatter as Formatter

version = 'Quasselgrep 0.1\nCopyright (c) 2013 Chris Le Sueur\nThis program is licensed under the GNU General Public License'
usage = '%prog [options] <keywords>'

def format_option_strings(self, option):
	"""Return a comma-separated list of option strings & metavariables."""
	if option.takes_value():
		metavar = option.metavar or option.dest.upper()
		if not option._long_opts:
			short_opts = [self._short_opt_fmt % (sopt, metavar)
					for sopt in option._short_opts]
		else:
			short_opts = option._short_opts

		long_opts = [self._long_opt_fmt % (lopt, metavar)
				for lopt in option._long_opts]
	else:
		short_opts = option._short_opts
		long_opts = option._long_opts

	if self.short_first:
		opts = short_opts + long_opts
	else:
		opts = long_opts + short_opts

	return ", ".join(opts)

Formatter.format_option_strings = format_option_strings

class QuasselGrep:
	def __init__(self):
		self.setup_optparser()

		self.server = None
		query = self.run()
		if query is None:
			return

		results = query.run()
		if query.options.debug:
			for res in results: print(res[0])
		elif results:
			for res in results: print(query.format(res))
		else:
			print("No results found.")

	def setup_optparser(self):
		"""Parse command line arguments using optarg"""
		parser = OptionParser(version=version, usage=usage, formatter=Formatter())
		parser.add_option('--db', dest='db_type', metavar='[postgres|sqlite]',
						  help='Type of database')
		parser.add_option('--dbname', dest='db_name', metavar='NAME',
						  help='Specify the database file or name.')
		parser.add_option('--dbuser', dest='db_user', metavar='DATABASE',
						  help='PostGres user')
		parser.add_option('--dbpassword', dest='db_password', metavar='DATABASE',
						  help='PostGres password')
		parser.add_option('--dbhost', dest='db_host', metavar='HOST',
						  help='Hostname of PostGres server')
		parser.add_option('--dbport', dest='db_port', metavar='PORT',
						  help='Port of PostGres server')

		parser.add_option('-c', '--configfile', dest='config', metavar='FILE',
				help='Location of config file')
		parser.add_option('-u', '--username', dest='username', metavar='USER',
					  help='Specify the quassel username.')
		parser.add_option('-N', '--network', dest='network', metavar='NETWORK',
					  help='Specify the network to search.')
		parser.add_option('-b', '--buffer', dest='buffer', metavar='BUFFER',
					  help='Specify the Quassel buffer (query nick or #channel) to search')
		parser.add_option('-n', '--nick', dest='sender', metavar='NICK',
					  help='Specify the nickname to search for')
		parser.add_option('-t', '--time', dest='timerange', metavar='RANGE',
					  help='Time range. See README for details.')
		parser.add_option('-i', '--inclusive', dest='inclusive', action='store_true',
		              help='Also search for joins, parts, etc.')
		parser.add_option('-L', '--limit', dest='limit', metavar='NUM',
		              help='Return at most NUM results')

		parser.add_option('--server', dest='server', action='store_true')
		parser.add_option('-H', '--host', dest='hostname', help='Connect to quasselgrep server at HOSTNAME')
		parser.add_option('-p', '--password', dest='password', help='Password your quassel username')

		parser.add_option('-l', dest='whole_line', action='store_true',
				help='Return only results whose message matches the entire search string')
		parser.add_option('-C', '--context', dest='context', metavar='LINES',
						  help='Include this many lines of context with results.')

		parser.add_option('--debug', dest='debug', action='store_true',
				help='Display information about the query instead of running it')

		self.parser = parser
		self.all_options = []
		self.valid_options = []
		for option in parser.option_list:
			if not option.dest:
				continue
			self.all_options.append(option.dest)

			if option.dest[:2] == 'db':
				continue
			if option.dest in ['hostname', 'config', 'server']:
				continue
			self.valid_options.append(option.dest)

	def parse_args(self, options=None):
		return self.parser.parse_args(values=options)

	def run(self, options=None, search='', salt=''):
		"""Main function called from the commandline"""

		#Set up command-line and configfile options
		if options:
			(options, args) = self.parse_args(options)
		else:
			(options, args) = self.parse_args()

		try:
			config.update_options(options)
		except ValueError as e:
			print("Error: Invalid option: %s" % (e))
			return

		if args:
			search = ' '.join(args)

		#Be a client, or a server.
		if options.hostname and not self.server:
			import client
			client.start(options, search, self)
			return
		if options.server and not self.server:
			import server
			self.server = True
			server.start(self, options)
			return

		db = Db()
		try:
			cursor = db.connect(options)
		except Exception as e:
			print("Error connecting to database: %s" % (e))
			return

		#Users connecting to a server need to authenticate
		if self.server:
			import server
			from util import salt_hash
			if not options.username or not options.password:
				raise server.AuthException('You must specify a quassel username and password.')

			cursor.execute('SELECT password FROM quasseluser WHERE username=%s' % (options.param_string), (options.username,))
			results = cursor.fetchall()
			if len(results) != 1:
				raise server.AuthException('Incorrect username or password.')
			if salt_hash(salt, results[0][0]) != options.password:
				raise server.AuthException('Incorrect username or password.')

		#If user requested a timerange, handle that
		if options.timerange:
			parser = dateparse.English()
			base = datetime.now()
			result = parser.parse(options.timerange, base)[0]
			if isinstance(result, timespan):
				start = result.start
				end = result.end
			else:
				start = result
				end = base

			if start:
				timerange = [start, end]
				print("Searching from %s to %s." % (start, end))
			else:
				timerange = None
				print("Error: Couldn't parse %s as a date/time." % (options.timerange))
				return
		else:
			timerange = None

		if not options.whole_line:
			search = '%%%s%%' % (search)

		#Create and run query
		query = Query(cursor, options, search, timerange)
		return query

	def server_request(self, command, socket):
		pass

def main():
	program = QuasselGrep()

if __name__ == '__main__':
	main()
