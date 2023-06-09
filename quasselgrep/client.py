from builtins import str
import sys
import socket
from argparse import _StoreFalseAction, _StoreTrueAction

from .util import salt_and_hash, getdata, escape

def start(options, search, program):
	if not getattr(options, 'hostname', None):
		print("Error: You must supply a hostname.")
		return
	if not getattr(options, 'password', None):
		print("Error: You must supply a password")
		return

	port = options.port if hasattr(options, 'port') else 9001

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((options.hostname, port))

	sock.send(b'HI\n')

	response = getdata(sock)[0]

	if response[:5] != 'SALT=':
		print('Error: Did not understand server response.')
		return

	salt = response[5:]
	options.password = salt_and_hash(salt, options.password)
	command = u''
	for option in program.parser._actions:
		opt_name = option.dest
		if not opt_name or not hasattr(options, opt_name):
			continue
		if not opt_name in program.valid_options:
			continue
		if getattr(options, opt_name) is None:
			continue
		value = getattr(options, opt_name)
		# A bit hackish: we need a value that will evaluate to false, and str(False) does not.
		# Ideally we should parse it properly on the server side, but it's hard.
		if isinstance(value, bool) or isinstance(option, (_StoreTrueAction, _StoreFalseAction)):
			value = u'1' if value else u''

		command += u'%s=%s\n' % (opt_name, escape(str(value)))

	command += u'SEARCH=%s\n' % (search)
	sock.sendall(command.encode('utf-8'))

	while True:
		data = sock.recv(1024)
		if not data:
			break
		sys.stdout.write(data.decode('utf-8'))

