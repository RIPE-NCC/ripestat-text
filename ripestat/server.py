"""
Module containing a ripestat-text whois-style server.

The executable script for the whois service lives at scripts/ripestat-whois.
"""
from optparse import OptionParser
import logging

from twisted.internet import reactor
from twisted.internet.error import CannotListenError
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

from ripestat.api import StatAPI
from ripestat.core import StatCore, StatCoreParser


logging.basicConfig()
LOG = logging.getLogger(__name__)


class StatTextServer(object):
    """
    Class for handling whois-style interaction with StatCore.
                LOG.exception(exc)
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
        Start the server with the provided options.
        """
        factory = WhoisFactory(self.options.base_url)
        success = False
        for interface in (self.options.interface or ["::"]):
            try:
                reactor.listenTCP(int(self.options.port), factory,
                    interface=interface)
            except CannotListenError as exc:
                LOG.error(exc)
            else:
                success |= True
        if success:
            reactor.run()
        else:
            LOG.error("Couldn't listen on any ports. Exiting.")
            return -1


class WhoisLineParser(StatCoreParser):
    """
    StatCoreParser subclass that responds to input from whois clients.
    """
    whois_option_list = [
        # make_option("-k", "--keep-alive", action="store_true",
        #    help="use a persistent connection")
    ]

    def __init__(self, protocol, *args, **kwargs):
        self.protocol = protocol
        StatCoreParser.__init__(self, *args, **kwargs)
        for option in self.whois_option_list:
            self.add_option(option)

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
    Twisted protocol that passes I/O between the client and StatCore.
    """
    delimiter = "\n"

    def connectionMade(self):
        """
        Initialize state when the client connects.
        """
        # Get the reader instance for this protocol
        readers = reactor.getReaders()
        for reader in readers:
            if getattr(reader, "protocol", None) == self:
                self.reader = reader
                break

    def lineReceived(self, line):
        """
        Parse a line of user input and pass it to StatCore.
        """
        # Don't accept any more data yet
        # This stops netcat from quitting before it gets the output!
        reactor.removeReader(self.reader)
        # Render the widgets in a separate thread
        reactor.callInThread(self.respond_to_client, line)

    def respond_to_client(self, line):
        """
        Execute the appropriate widgets and queue the output for sending from
        the main thread.
        """
        params = line.strip().split()  # We need to accept trailing \r

        parser = WhoisLineParser(self)
        options, args = parser.parse_args(params)

        core = StatCore(self.output, api=self.factory.api, parser=parser)
        core.main(params)

        reactor.callFromThread(self.transport.loseConnection)

    def output(self, line):
        """
        Callback method to allow StatCore to send output over the network.

        Each line is queued in the main thread for sending.
        """
        reactor.callFromThread(self.sendLine, line.encode("utf-8"))


class WhoisFactory(Factory):
    """
    Twisted factory that uses the WhoisProtocol.
    """
    protocol = WhoisProtocol

    def __init__(self, base_url):
        self.api = StatAPI("whois", base_url)
