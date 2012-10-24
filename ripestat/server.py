"""
Module containing a ripestat-text whois-style server.

The executable script for the whois service lives at scripts/ripestat-whois.
"""
from optparse import OptionParser
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor

from ripestat.api import StatAPI
from ripestat.core import StatCore, StatCoreParser


class StatTextServer(object):
    """
    Class for handling whois-style interaction with StatCore.
    """
    parser = OptionParser()
    parser.add_option("-p", "--port", default="43")
    parser.add_option("-b", "--base-url",
        default="https://stat.ripe.net/data/")
    parser.add_option("-i", "--interface", action="append" )

    def __init__(self, params):
        self.options, self.args = self.parser.parse_args(params)

    def start(self):
        """
        Start listening on the given port.
        """
        factory = WhoisFactory(self.options.base_url)
        for interface in (self.options.interface or ["::"]):
            reactor.listenTCP(int(self.options.port), factory,
                interface=interface)
        reactor.run()


class WhoisLineParser(StatCoreParser):
    """
    StatCoreParser subclass that responds to input from whois clients.
    """
    def __init__(self, protocol, *args, **kwargs):
        self.protocol = protocol
        StatCoreParser.__init__(self, *args, **kwargs)

    def print_help(self, *args, **kwargs):
        for line in  self.format_option_help().split("\n"):
            self.protocol.output(line)

    def print_usage(self, *args, **kwargs):
        self.print_help()

    def exit(self, *args, **kwargs):
        """
        The whois parser should never exit.
        """
        pass


class WhoisProtocol(LineReceiver):
    """
    Twisted protocol that passes I/O between the user and StatCore.
    """
    def lineReceived(self, line):
        """
        Parse a line of user input and pass it to StatCore.
        """
        parser = WhoisLineParser(self)
        core = StatCore(self.output, api=self.factory.api,
            parser=parser)
        core.main(line.split())
        self.transport.loseConnection()

    def output(self, line):
        """
        Callback method to allow StatCore to send output over the network.
        """
        self.sendLine(line.encode("utf-8"))


class WhoisFactory(Factory):
    """
    Twisted factory that uses the WhoisProtocol.
    """
    protocol = WhoisProtocol

    def __init__(self, base_url):
        self.api = StatAPI("whois", base_url)
