defaults = {
	'db_type' : 'sqlite',
	'db_name' : 'quassel-storage.sqlite',
	'db_user' : None,
	'db_password' : None,
}
def update_options(options):
	conf_file = options.config
	namespace = {}
	config = defaults

	try:
		execfile(conf_file, namespace)
	except IOError:
		print "Error: Could not open %s for reading; ignoring." % (conf_file)
	else:
		if 'config' not in namespace or not isinstance(namespace['config'], dict):
			raise ValueError('%s is not a valid config file (Does not have a dict named "config")' % (conf_file))
		config.update(namespace['config'])

	for (key, value) in config.items():
		if not getattr(options, key, None):
			setattr(options, key, value)
	
