"""
Module containing a ripestat-text whois-style server.

The executable script for the whois service lives at scripts/ripestat-whois.
"""
from optparse import make_option
from Queue import Queue

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log

from ripestat.api import StatAPI
from ripestat.core import StatCore, StatCoreParser


log.PythonLoggingObserver().start()


class StatTextProtocol(LineOnlyReceiver):
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
        self.keep_alive = False
        self.input_lines = Queue()
        client = self.transport.getPeer()
        log.msg("Connection from {0}".format(client))

        self.api = StatAPI("whois", self.factory.base_url,
            headers=[("X-Forwarded-For", client.host)])

    def dataReceived(self, data):
        """
        Overridden to stop trying to read data while outputting a response.

        This stops netcat from quitting before it gets the output!
        """
        reactor.removeReader(self.reader)
        retval = LineOnlyReceiver.dataReceived(self, data)
        reactor.callInThread(self.processLines)
        return retval

    def lineReceived(self, line):
        """
        Parse a line of user input and render the widgets.
        """
        log.msg("Query: {1!r}".format(self.transport.getPeer().host, line))
        self.input_lines.put(line)

    def processLines(self):
        """
        Render a set of widgets for each input line on the queue.
        """
        while self.input_lines.qsize():
            line = self.input_lines.get()
            self.renderWidgets(line)
            self.input_lines.task_done()

        # Maintain or end the connection depending on the mode
        if self.keep_alive:
            reactor.callFromThread(reactor.addReader, self.reader)
        else:
            reactor.callFromThread(self.transport.loseConnection)

    def renderWidgets(self, line):
        """
        Execute the appropriate widgets and queue the output for sending from
        the main thread.
        """
        params = line.strip().split()  # We need to accept trailing \r

        parser = StatTextLineParser(self)
        options, args = parser.parse_args(params)

        # Render the widgets if the input wasn't a single keep_alive flag
        if not (options.keep_alive and not args):
            core = StatCore(self.queueLine, api=self.api, parser=parser)
            core.main(params)

        if options.keep_alive:
            self.keep_alive = not self.keep_alive

    def queueLine(self, line):
        """
        Callback method to allow StatCore to send output over the network.

        Each line is queued in the main thread for sending.
        """
        reactor.callFromThread(self.sendLine, line.encode("utf-8"))


class StatTextFactory(Factory):
    """
    Twisted factory that uses the StatTextProtocol.
    """
    protocol = StatTextProtocol

    def __init__(self, base_url):
        self.base_url = base_url


class StatTextLineParser(StatCoreParser):
    """
    StatCoreParser subclass that responds to input from whois clients.
    """
    whois_option_list = [
        make_option("-k", "--keep-alive", action="store_true",
            help="use a persistent connection")
    ]

    def __init__(self, protocol, *args, **kwargs):
        self.protocol = protocol
        StatCoreParser.__init__(self, *args, **kwargs)
        for option in self.whois_option_list:
            self.add_option(option)

    def print_help(self, *args, **kwargs):
        for line in  self.format_option_help().split("\n"):
            self.protocol.queueLine(line)

    def print_usage(self, *args, **kwargs):
        self.print_help()

    def exit(self, *args, **kwargs):
        """
        The whois parser should never exit.
        """
        pass
