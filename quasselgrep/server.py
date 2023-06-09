from future import standard_library
standard_library.install_aliases()
from builtins import object
from socketserver import ThreadingTCPServer, TCPServer, BaseRequestHandler
from shlex import split
from os import urandom

from .util import getdata

class AuthException(Exception):
	pass

class Object(object):
	pass

class QuasselGrepHandler(BaseRequestHandler):
	def handle(self):
		socket = self.request
		program = self.server.program
		request = getdata(socket)[0]

		if request != 'HI':
			socket.sendall(b'GO AWAY\n')
			socket.close()
			return

		salt = urandom(32).encode('hex')
		socket.sendall(b'SALT=%s\n' % (salt))

		option_list = []
		while True:
			new = getdata(socket)
			if new[-1] == '':
				option_list += new[:-1]
				break
			option_list += new

		#valid_options = [opt.dest for opt in self.server.program.parser.option_list if opt.dest]
		options = Object()
		search = ''
		for opt in program.all_options:
			setattr(options, opt, None)

		for option in option_list:
			option = option.split('=')
			if len(option) != 2:
				continue
			if option[0] == 'SEARCH':
				search = option[1]
				continue
			#Sanity/safety check
			if option[0] not in program.valid_options:
				continue
			setattr(options, option[0], option[1])

		#if response[:5] != 'AUTH=':
		#	socket.sendall('GO AWAY\n')
		#	socket.close()
		#	return

		#password = response[5:]

		try:
			query = program.run(options, search, salt)
		except AuthException as e:
			socket.sendall(('Error: %s\n' % (e)).encode('utf-8'))
			socket.close()
			return

		socket.sendall(b'Please wait for results...\n')
		results = query.run()
		if results:
			for res in results:
				socket.sendall((query.format(res) + '\n').encode('utf-8'))
			socket.close()
		else:
			socket.sendall(b'No results.\n')

host = ''
port = 9001
def start(program, options):
	ThreadingTCPServer.allow_reuse_address = True
	server = ThreadingTCPServer((host, port), QuasselGrepHandler)
	server.program = program
	server.options = options

	server.serve_forever()
	print("Finishing.")
