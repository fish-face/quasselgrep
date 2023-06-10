quasselgrep
===========

Tool for searching quassel logs from the commandline

[![Packaging status](https://repology.org/badge/tiny-repos/quasselgrep.svg)](https://repology.org/project/quasselgrep/versions)
[Gentoo overlay](https://github.com/jjakob/gentoo-overlay/net-irc/quasselgrep)

Requirements
---

Mandatory:
- python-dateutil

Optional:
- python-crypto (to run as client/server)
- psycopg2 (for PostgreSQL support)

Installation
---

You don't need to install quasselgrep to use it but it might be more convenient. Install it via your system's package manager.

If a package is not available for your OS, you can install it with pip:

	# sudo pip install .

from the root directory. You can also install it as a local user or in a virtualenv or by directly running setup.py. Having done this you will be able to run the `quasselgrep` command at the shell. If you don't install it like this, either use:

	$ ./launch.py <options>

or

	$ python -m quasselgrep <options>

from the root directory. From now on it is assumed that you have installed quasselgrep in the normal way, though.

Usage
---

The basic usage is:

```
$ quasselgrep [OPTIONS] <search text>
```

The help message (`quasselgrep --help`) should explain most options.
Text fields are searched using SQL LIKE statements, so you can use '%' as a wildcard.

By default, quasselgrep will try to open an sqlite database at `~/.config/quassel-irc.org/quassel-storage.sqlite`. You can specify an alternative database file on the commandline.

It is also possible to search in a postgres database:

	$ quasselgrep --db postgres [...]

This will attempt to connect to a database named "quassel" on localhost with port 5432, and no username and password.
To specify authentication details, use the `--dbuser` and `--dbpassword` options or use a config file.

If quasselgrep can connect to a database then it can see all backlog, for any quassel user.
Quasselgrep can be run as a server on a quassel host, and quasselgrep clients can connect.
See the relevant sections for how to run quasselgrep as a server, or use it to connect to one.

You can get context around search results with the -C option, making it easier to work out what was going on at the time someone said something.
This is quite database-intensive, and is in any case best used for queries that will return few results (e.g. using a short time-period.)
In particular, using this option without either the `-t` or `-b` options is liable to be inordinately slow.

Examples
---

Search for any messages for any user saying 'Hello!':

    $ quasselgrep Hello!

Search for any messages on #quassel from Sput:

    $ quasselgrep -b #quassel -n Sput

Search for messages for a particular quassel user, sent yesterday:

    $ quasselgrep -u MyUser -t yesterday [...]

Search for messages in a particular channel, sent at most four days ago and give 3 lines of context either side of each result:

    $ quasselgrep -b #chat -t -5d -C 3 [...]

Searching by date/time
---

Quasselgrep uses code from the Whoosh project to provide a huge array of time filtering options.
If Quasselgrep can't parse the date/time you provided, you can always fall back to ISO-formatted dates:

    $ quasselgrep -t 2013-10-09 [...]

will limit output to messages on the 9th of October, 2013.
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

Running/Connecting to a Quasselgrep Server
---

If you host a Quassel server, you can run quasselgrep on it so that your users can search their logs easily.
Just run quasselgrep as follows:

	$ quasselgrep [db-options] --server

You can specify other options on the commandline; these will restrict users to using only those parameters and is probably not useful in the slightest.
On the other hand, any options you specify in the config file are taken as defaults and can be overridden.
Quasselgrep listens on port 9001 by default, and you can specify an alternative with `--port`.

Running a quasselgrep server means allowing all your quassel users to run potentially expensive queries against the database, which could impact performance of the server for other users.
Options for limiting queries to guard against accidental DoS attacks should be coming soon.

To connect to a quasselgrep server, supply the `-H/--hostname` option, specifying the server to connect to.
You will also need to supply your quassel username and password:

    $ quasselgrep -H <hostname> [--port <port>] -u <user> --password <password> [...]

Your password is not transmitted in the clear, but all other communication is.

Performance
---

Quassel's backlog constitutes a rather large database table, so some queries are going to take a while to run.
That said, Quasselgrep shouldn't be too slow with a reasonably-sized PostgreSQL database, for reasonable queries, so let me know if you're in this situation but are experiencing slowness.
One thing that can make a big difference is adding a database index for message times; this means that a search for results with the `-t` parameter are much more efficient.
To do this, connect to the database as the quassel user and run the following command:

```sql
CREATE INDEX CONCURRENTLY backlog_time ON backlog (time);
```

(Don't attempt to do this if you don't know what you're doing)

Of course if you're using SQLite, all bets are off!
See the [migration page](http://bugs.quassel-irc.org/projects/1/wiki/PostgreSQL) on the Quassel site for instructions on how to migrate if this is causing issues.

My own database is under 500M in size and so information on performance with larger databases is welcome.

quasselgrep.conf
---

Principally for storing database connection information, a configfile can be created and specified with the -c option (Default: `~/.quasselgrep.conf`)
The file should look something like:

```python
config = {
	'db_type' : 'postgres',
	'db_name' : 'quassel',
	'db_user' : 'quassel',
	'db_password' : '<DatabasePassword>',
	'db_host' : 'localhost',
	'username' : '<MyQuasselUser>'
}
```

You can also preset search options if you wish.
Any settings in the config file will be overridden by command-line options.
