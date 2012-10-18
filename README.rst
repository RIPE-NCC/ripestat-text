ripestat-text
-------------

Licence
=======
This package is distributed under the terms of the LGPL v3 or later:

    https://raw.github.com/RIPE-NCC/ripestat-text/latest/LICENCE

Installation
============

You can install the package system wide by running the following command in 
the source directory::

    $ python setup.py install

or to install for a single user::

    $ python setup.py install --user; export PATH=$PATH:~/.local/bin

You can always upgrade to the latest release with this command::

    $ easy_install -U https://github.com/RIPE-NCC/ripestat-text/tarball/latest

Overview
========
This package contains several components, notably:

    * the RIPEstat command-line client (ripestat)
    * the RIPEstat whois server (ripestat-whois-server)
    * the text widgets that are shared between the two
    * a Python library to help you use the data API from your Python programs

CLI
===
The CLI client allows you to query RIPEstat using a Python script on your
computer. After installing this package the client will be available to you.

To get started, try::

    $ ripestat --help

or to get all kinds of information about your current network::

    $ ripestat `ripestat --data-call whats-my-ip --select ip`

The CLI has two main operating modes:

    * displaying semi-structured information intended for humans and light scripting (see the --widgets and --list-widgets options)
    * querying and filtering the RIPEstat Data API for heavier scripting (see --data-call, --list-data-calls, --select and --template)

Widgets
=======
A ripestat-text "widget" is a way of presenting information from RIPEstat in
a whois-style format that is human readable while being semi-structured and
parseable.

These widgets are equivalent to the web widgets on the stat.ripe.net website.
Like the web widgets, they pull information from the RIPEstat Data API.

A few widgets have been included with ripestat-text. For those data calls that
don't yet have a widget, there is a default rendering which takes the data call
response and renders it to a whois-style format that is at least partially
readable and parseable.

Everyone is encouraged to create widgets and propose them on github:

    https://github.com/RIPE-NCC/ripestat-text

Data scripting
==============
It is possible to use the data API for heavier scripting using the data call 
options. In particular::

    -s bla.*.bla   (select data using dot notation and glob matching)

    -t 'prefix: {prefix}'   (render matched items using string templating)

For example, to get a list of prefixes that have historically been announced 
by a certain ASN, sorted by the time they were first announced::

    $ ripestat as3333 -d routing-history -s by_origin.*.prefixes \
            -t '{timelines.0.starttime} {prefix}' | sort
    2000-08-20T00:00:00 193.0.0.0/22
    2000-09-09T00:00:00 193.0.0.0/21
    2002-06-06T16:00:00 192.16.202.0/24
    ...

Whois service
=============
A whois service with largely the same functionality as the CLI is available at
stat.ripe.net on port 43. The biggest difference at the moment is that the
whois service doesn't support any form of authentication.

You can access the service using a whois client of your choice. You may need to
use quotes for the params to be sent to the server, so that they don't get 
parsed by your client. For example::

    $ whois -h stat.ripe.net " 193/24 --widgets object-browser,prefix-overview"

To get a full list of options, you can do::
    
    $ whois -h stat.ripe.net " --help"

*(Note the leading space within the quotes.)*

Python API
==========
ripestat-text uses a simple Python module for querying the RIPEstat Data API.
This module is included in the package and can be used by third-party scripts.

As a quick example, this snippet will print the IP address used to contact
RIPEstat::

    from ripestat.api import StatAPI
    api = StatAPI("my-first-ripestat-script")
    print("Outgoing IP address: {ip}".format(**api.get_data("whats-my-ip")))
