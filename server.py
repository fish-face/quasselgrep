from SocketServer import ThreadingTCPServer, TCPServer, BaseRequestHandler
from shlex import split
from os import urandom

from util import getdata

class AuthException(Exception):
	pass

class Object:
	pass

class QuasselGrepHandler(BaseRequestHandler):
	def handle(self):
		socket = self.request
		request = getdata(socket)[0]

		if request != 'HI':
			socket.sendall('GO AWAY\n')
			socket.close()
			return

		salt = urandom(32).encode('hex')
		socket.sendall('SALT=%s\n' % (salt))

		option_list = []
		while True:
			new = getdata(socket)
			if new[-1] == 'GO' or new[-1] == '':
				option_list += new[:-1]
				break
			option_list += new

		valid_options = [opt.dest for opt in self.server.program.parser.option_list if opt.dest]
		options = Object()
		for opt in valid_options:
			setattr(options, opt, None)

		for option in option_list:
			option = option.split('=')
			if len(option) != 2:
				continue
			#Sanity/safety check
			if option[0] not in valid_options or option[0][:2] == 'db' or option[0] == 'config':
				continue
			setattr(options, option[0], option[1])

		#if response[:5] != 'AUTH=':
		#	socket.sendall('GO AWAY\n')
		#	socket.close()
		#	return

		#password = response[5:]

		print "Running:", options
		try:
			query = self.server.program.run(options, salt)
		except AuthException, e:
			socket.sendall('Error: %s' % (e))
			socket.close()
			return

		socket.sendall('Please wait for results...\n')
		print "running query"
		results = query.run()
		print "run:", len(results)
		if results:
			print 'Query finished'
			for res in results:
				socket.sendall(query.format(res) + '\n')
			socket.close()
		else:
			socket.sendall('No results.')

host = 'localhost'
port = 9001
def start(program, options):
	ThreadingTCPServer.allow_reuse_address = True
	server = ThreadingTCPServer((host, port), QuasselGrepHandler)
	server.program = program
	server.options = options

	server.serve_forever()
	print "Finishing."
