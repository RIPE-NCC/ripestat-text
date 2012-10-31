"""
Module containing a ripestat-text command-line interface.

The executable script for the CLI lives at scripts/ripestat.
"""
from getpass import getpass
from optparse import OptionGroup, make_option
import logging
import os
import sys

from ripestat.api import StatAPI
from ripestat.core import StatCore
from ripestat.parser import BaseParser


class StatCLIParser(BaseParser):
    """
    Parser that knows about CLI specific options.
    """
    # Options for SSO authentication
    auth_option_list = [
        make_option("-u", "--username", help="your RIPE NCC Access "
            "e-mail address"),
        make_option("-g", "--login", help="login subsequent requests "
            "from this shell", action="store_true"),
        make_option("--password", help="your RIPE NCC Access password"
            " (will appear in `ps` listings etc)")
    ]

    # Debug options
    extra_option_list = [
        make_option("--tracebacks", help="Show full error reports when "
        "widgets fail", action="store_true")
    ]

    def __init__(self, *args, **kwargs):
        BaseParser.__init__(self, *args, **kwargs)

        auth_group = OptionGroup(self, "Authentication Options")
        for option in self.auth_option_list:
            auth_group.add_option(option)
        self.add_option_group(auth_group)

        for option in self.extra_option_list:
            self.add_option(option)


class StatCLI(object):
    """
    Class for handling command-line interaction with StatCore.
    """
    parser = StatCLIParser()

    def __init__(self):
        logger = logging.getLogger(None)
        logger.setLevel(logging.CRITICAL)

    def output(self, line):
        """
        Callback for outputting lines from the StatCore class.
        """
        print(line.encode("utf-8"))

    def main(self, params):
        """
        Process some command line parameters and pass them to StatCore.
        """
        base_url = os.environ.get("STAT_URL", "https://stat.ripe.net/data/")
        token = os.environ.get("STAT_TOKEN")

        options, args = self.parser.parse_args(params)

        logger = logging.getLogger(None)
        if options.tracebacks:
            logger.setLevel(logging.ERROR)
        else:
            logger.setLevel(logging.CRITICAL)

        api = StatAPI("cli", base_url=base_url, token=token)
        stat = StatCore(self.output, parser=self.parser, api=api)
        if (options.login or options.password) and not options.username:
            options.username = self.get_input("username: ")
        if options.username:
            password = options.password
            if not password:
                password = os.environ.get("STAT_PASSWORD")
            if not password:
                password = getpass("password: ")
            success = stat.api.login(options.username, password)
            if not success:
                self.output("Failed to authenticate.")
            if options.login:
                if not success:
                    return 1
                token = stat.api.get_session()
                self.output("STAT_TOKEN=" + token +
                    "; export STAT_TOKEN; echo STAT_TOKEN has been set. You are now logged in to RIPEstat with this shell.")
                return 0
        return stat.main(params)

    def get_input(self, prompt):
        """
        Prompt to tty or stdout, and read from tty or stdin.
        """
        try:
            out_stream = open("/dev/tty", "w+")
            in_stream = out_stream
        except EnvironmentError:
            # If tty is unavailable or we are in a non-POSIXy environment
            out_stream = sys.stdout
            in_stream = sys.stdin
        out_stream.write(prompt)
        return in_stream.readline()
