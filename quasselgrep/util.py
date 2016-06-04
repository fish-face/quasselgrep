from Crypto.Hash import SHA

def getdata(socket):
	command = ''
	while True:
		data = socket.recv(1024)
		if not data:
			break
		command += data
		if data[-1] == '\n':
			break

	return command.split('\n')

def salt_and_hash(salt, password):
	h = SHA.new()
	h.update(password)
	pwhash = h.hexdigest()

	return salt_hash(salt, pwhash)

def salt_hash(salt, pwhash):
	h = SHA.new()
	h.update(salt)
	h.update(pwhash)

	return h.hexdigest()

def escape(string):
	string = string.replace('\\', r'\\')
	string = string.replace('\n', r'\n')
	return string

