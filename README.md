quasselgrep
===========

Tool for searching quassel logs from the commandline

Requirements
---

The python dateutil library is a requirement, and can be installed with pip:

    # pip install python-dateutil

Usage
---

The help message (`quasselgrep --help`) should explain most options.
By default, quasselgrep will try to open an sqlite database named `quassel-storage.sqlite` in the current folder. You can specify an alternative database file on the commandline:

    $ quasselgrep --dbname ~/.config/quassel-storage.sqlite [...]

It is also possible to search in a postgres database:

	$ quasselgrep --db postgres [...]

This will attempt to connect to a database named "quassel" on localhost with port 5432, and no username and password.
To specify authentication details, use the `--dbuser` and `--dbpassword` options or use a config file.

If quasselgrep can connect to a database then it can see all backlog, for any quassel user.
Therefore it is not currently suitable for a multi-user quassel server, although it is possible to limit searches to a particular user with the -u switch.

Examples
---

Search for any messages for any user saying 'Hello!':

    $ quasselgrep 'Hello!'

Search for any messages on #quassel from Sput:

    $ quasselgrep -b '#quassel' -n Sput% %

Search for messages for a particular quassel user, sent yesterday:

    $ quasselgrep -u 'MyUser' -t yesterday [...]

Search for messages in a particular channel, sent at most four days ago:

    $ quasselgrep -b '#chat' -t -5d [...]

Searching by date/time
---

Quasselgrep uses code from the Whoosh project to provide a huge array of time filtering options.
If Quasselgrep can't parse the date/time you provided, you can always fall back to ISO-formatted dates:

    $ quasselgrep -t 2013-10-10 [...]

will limit output to messages on the 10th of October, 2013.
A single date or time will specify a range, so that:

	$ quasselgrep -t December [...]

will only display messages from December of the current year.
You can also specify a range manually:

    $ quasselgrep -t "5th Dec to 8th Dec 7PM" [...]

will find messages from 00:00 on the 5th of December until 19:59 on the 8th.
Some English-language phrases are also supported:

    $ quasselgrep -t "yesterday to 2pm today" [...]

will do the obvious thing.
Relative searches are also possible:

    $ quasselgrep -t "-2months" [...]

find messages from two months ago until now.
You can also use "years", "days" and so on, as well as abbreviations "yr", "y", "hr", "h" etc.

quasselgrep.conf
---

Principally for storing database connection information, a configfile can be created and specified with the -c option (Default: `quasselgrep.conf` in the current directory)
The file should look something like:

```python
config = {
	'db_type' : 'postgres',
	'db_name' : 'quassel',
	'db_user' : 'quassel',
	'db_password' : '<DatabasePassword>',
	'db_host' : 'localhost',
	'user' : '<MyQuasselUser>'
}
```

You can also preset search options if you wish.
Any settings in the config file will be overridden by command-line options.
