"""
Module containing a ripestat-text whois server.

The executable script for the whois service lives at scripts/ripestat-whois.
"""
from getopt import gnu_getopt
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

from ripestat.api import StatAPI
from ripestat.core import StatCore


class WhoisProtocol(LineReceiver):
    """
    Twisted protocol that passes I/O between the user and StatCore.
    """

    def lineReceived(self, line):
        """
        Parse a line of user input and pass it to StatCore.
        """
        api = StatAPI("whois", base_url=self.factory.base_url)
        core = StatCore(self.script_output, api=api)
        core.main(line.split())
        self.transport.loseConnection()

    def script_output(self, line):
        """
        Callback method to allow StatCore to send output over the network.
        """
        self.sendLine(line.encode("utf-8"))


class WhoisFactory(Factory):
    """
    Twisted factory that uses the WhoisProtocol.
    """
    protocol = WhoisProtocol


class StatWhoisServer(object):
    """
    Class for handling whois interaction with StatCore.
    """

    def __init__(self, params):
        self.options, self.args = gnu_getopt(params, "")

    def start(self):
        """
        Start listening on the given port.
        """
        endpoint = TCP4ServerEndpoint(reactor, int(self.args[0]))
        factory = WhoisFactory()
        factory.base_url = self.args[1]
        endpoint.listen(factory)
        reactor.run()
