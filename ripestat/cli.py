"""
Module containing a ripestat-text command-line interface.

The executable script for the CLI lives at scripts/ripestat.
"""
import sys
import os
from getpass import getpass
from optparse import OptionGroup

from ripestat.api import StatAPI
from ripestat.core import StatCore, UsageError, OtherError


class StatCLI(object):
    """
    Class for handling command-line interaction with StatCore.
    """
    parser = StatCore.parser
    option_group = OptionGroup(parser, "Authentication Options")
    option_group.add_option("-u", "--username", help="your RIPE NCC Access "
        "e-mail address")
    option_group.add_option("-g", "--login", help="login subsequent requests "
        "from this shell", action="store_true")
    option_group.add_option("--password", help="your RIPE NCC Access password"
        " (will appear in `ps` listings etc)")
    parser.add_option_group(option_group)

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

        api = StatAPI(base_url=base_url, token=token, caller_id="cli")
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
        try:
            return stat.main(params)
        except UsageError as exc:
            if exc.message:
                self.output(exc.message)
                self.output("")
            print(self.parser.format_option_help())
            return 1
        except OtherError as exc:
            self.output(exc.message)
            return 2

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
