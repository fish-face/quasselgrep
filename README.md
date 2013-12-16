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
By default, quasselgrep will try to open an sqlite database at `~/.config/quassel-irc.org/quassel-storage.sqlite`. You can specify an alternative database file on the commandline.

It is also possible to search in a postgres database:

	$ quasselgrep --db postgres [...]

This will attempt to connect to a database named "quassel" on localhost with port 5432, and no username and password.
To specify authentication details, use the `--dbuser` and `--dbpassword` options or use a config file.

If quasselgrep can connect to a database then it can see all backlog, for any quassel user.
Therefore it is not currently suitable for a multi-user quassel server, although it is possible to limit searches to a particular user with the -u switch.

You can get context around search results with the -C option, making it easier to work out what was going on at the time someone said something.
This is quite database-intensive, and is in any case best used for queries that will return few results (e.g. using a short time-period.)

Examples
---

Search for any messages for any user saying 'Hello!':

    $ quasselgrep 'Hello!'

Search for any messages on #quassel from Sput:

    $ quasselgrep -b '#quassel' -n Sput% %

Search for messages for a particular quassel user, sent yesterday:

    $ quasselgrep -u 'MyUser' -t yesterday [...]

Search for messages in a particular channel, sent at most four days ago and give 3 lines of context either side of each result:

    $ quasselgrep -b '#chat' -t -5d -C 3 [...]

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

Performance
---

Quassel's backlog constitutes a rather large database table, so some queries are going to take a while to run.
That said, Quasselgrep shouldn't be too slow with a reasonably-sized PostgreSQL database, for reasonable queries, so let me know if you're in this situation but are experiencing slowness.

Of course if you're using SQLite, all bets are off!
See the [migration page](http://bugs.quassel-irc.org/projects/1/wiki/PostgreSQL) on the Quassel site for instructions on how to migrate if this is causing issues.

My own database is under 500M in size and so information on performance with larger databases is welcome.

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
