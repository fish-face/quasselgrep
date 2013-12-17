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

def update_options(options):
	conf_file = options.config
	namespace = {}
	config = defaults

	use_config = True

	if conf_file:
		try:
			execfile(conf_file, namespace)
		except IOError:
			print "Error: Could not open %s for reading; ignoring." % (conf_file)
			use_config = False
	else:
		try:
			execfile(defaults['config'], namespace)
		except IOError:
			use_config = False

	if use_config:
		if 'config' not in namespace or not isinstance(namespace['config'], dict):
			raise ValueError('%s is not a valid config file (Does not have a dict named "config")' % (conf_file))
		config.update(namespace['config'])

	for (key, value) in config.items():
		if not getattr(options, key, None):
			setattr(options, key, value)
	
	if options.db_type and options.db_type not in ('sqlite', 'postgres'):
		raise ValueError("dbtype must be one of sqlite or postgres, not '%s'" % (options.db_type))
	if options.context:
		try:
			n = int(options.context)
		except:
			raise ValueError("Context must be an integer, not %s" % (options.context))
	
