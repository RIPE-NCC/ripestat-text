from getopt import gnu_getopt
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

from ripestat.core import Stat


class Whois(LineReceiver):

    def lineReceived(self, line):
        cmd = Stat(callback=self.script_output, base_url=self.factory.base_url,
            caller_id="whois")
        cmd.main(line.split())
        self.transport.loseConnection()

    def script_output(self, line):
        self.sendLine(line.encode("utf-8"))


class WhoisFactory(Factory):
    protocol = Whois


class StatWhoisServer(object):

    def __init__(self, params):
        self.options, self.args = gnu_getopt(params, "")

    def start(self):
        endpoint = TCP4ServerEndpoint(reactor, int(self.args[0]))
        factory = WhoisFactory()
        factory.base_url = self.args[1]
        endpoint.listen(factory)
        reactor.run()
