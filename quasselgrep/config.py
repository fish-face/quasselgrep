import os

defaults = {
	'config' : os.path.expanduser('~/.quasselgrep.conf'),
	'db_type' : 'sqlite',
	'db_name' : os.path.expanduser('~/.config/quassel-irc.org/quassel-storage.sqlite'),
	'db_user' : None,
	'db_password' : None,
	'db_host' : 'localhost',
	'db_port' : 5432,
	'db_password' : None,

	'whole_line' : False
}

def loadconfig(filename, namespace):
    with open(filename, 'rbU') as fd:
        source = fd.read()
    code = compile(source, filename, 'exec')
    exec(code, namespace)

def update_options(options):
	conf_file = options.config
	namespace = {}
	config = defaults

	use_config = True

	if conf_file:
		try:
			loadconfig(conf_file, namespace)
		except IOError:
			print("Error: Could not open %s for reading; ignoring." % (conf_file))
			use_config = False
	else:
		try:
			loadconfig(defaults['config'], namespace)
		except IOError:
			use_config = False

	if use_config:
		if 'config' not in namespace or not isinstance(namespace['config'], dict):
			raise ValueError('%s is not a valid config file (Does not have a dict named "config")' % (conf_file))
		config.update(namespace['config'])

	for (key, value) in list(config.items()):
		if not getattr(options, key, None):
			setattr(options, key, value)

	if options.db_type not in ('sqlite', 'postgres'):
		raise ValueError("dbtype must be one of sqlite or postgres, not '%s'" % (options.db_type))
	if options.context:
		try:
			options.context = int(options.context)
			assert options.context >= 0
		except:
			raise ValueError("Context must be a non-negative integer, not %s" % (options.context))
	if options.db_type == 'sqlite' and options.context:
		raise ValueError('Printing context is not currently supported with an SQLite database')

	if options.limit:
		try:
			n = int(options.limit)
		except:
			raise ValueError("Limit must be an integer, not %s" % (options.limit))

