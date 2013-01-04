"""
Module containing the main parsing/dispatching functionality for ripestat-text.

The 'whois' and 'cli' interfaces both use this module.
"""
import logging

from ripestat import __version__
from ripestat.whois import WhoisSerializer
from ripestat.data import DataProcessor
from ripestat.rendering import WidgetRenderer
from ripestat.parser import BaseParser, UserError


class StatCore(DataProcessor, WidgetRenderer):
    """
    Class encapsulating the core functionality of ripestat-text.

    Calling classes can specify their own parser with more options. These
    custom parsers must however subclass BaseParser.
    """
    def __init__(self, callback, api, parser=None):
        logging.basicConfig()
        self.logger = logging.getLogger("ripestat")

        # This function is called whenever something needs to be output to the
        # user.
        self.output = callback

        self.api = api

        if parser:
            assert isinstance(parser, BaseParser), ("Custom parsers must "
                "subclass parser.BaseParser")
            self.parser = parser
        else:
            self.parser = BaseParser()

        self.serializer = WhoisSerializer()

    def main(self, args):
        """
        Process the command line from the user and print a response to stdout.

        This method calls self._main() so that it can catch UserError.
        """
        try:
            return self._main(args)
        except UserError as exc:
            if exc.message:
                self.output(exc.message)
                if exc.show_help:
                    self.output("")
            if exc.show_help:
                self.output(self.parser.format_option_help())
            return 1

    def _main(self, args):
        """
        Internal method for responding to a command line.

        May raise UserError.
        """
        options, args = self.parser.parse_args(args)

        if options.verbose == 1:
            self.logger.setLevel(logging.INFO)
        elif options.verbose and options.verbose >= 2:
            self.logger.setLevel(logging.DEBUG)

        if options.version:
            return self.show_version()
        elif options.help:
            return self.parser.print_help()
        elif options.list_widgets:
            return self.list_widgets()
        elif options.list_data_calls:
            return self.list_data_calls()
        elif options.explain_data_call:
            return self.explain_data_call(options.explain_data_call)

        query = StatQuery(*args)

        if options.data_call and options.widgets:
            raise UserError(
                "--data-call and --widgets are conflicting options",
                    show_help=True)
        elif options.data_call:
            self.api.caller_id += "/data-call"
            try:
                return self.output_data(options.data_call, query,
                    include_metadata=options.include_metadata,
                    abbreviate=options.abbreviate_data, select=options.select,
                    template=options.template)
            except self.api.ServerError as exc:
                if exc.status_code == 400:
                    raise UserError(exc.args[0], show_help=False)
        else:
            self.api.caller_id += "/widgets"
            return self.output_widgets(options.widgets, query,
                include_metadata=options.include_metadata,
                preserve_order=options.preserve_order)

    def show_version(self):
        """
        Output the public ripestat-text version label.
        """
        self.output(unicode(__version__))

    def output_whois(self, lines, **kwargs):
        """
        Output the given lines in a whois style format.
        """
        output = self.serializer.dumps(lines, **kwargs)
        self.output(output)



class StatQuery(dict):
    """
    A dictionary of parameters for passing to a widget or data call.
    """
    __slots__ = "resource_type"

    def __init__(self, *args):
        """
        Convert positional key=value arguments to a Python dict.

        >>> query = StatQuery("year=2011", "limit=5", "as3333")
        >>> query == {
        ...    "year": "2011",
        ...    "limit": "5",
        ...    "resource": "as3333"
        ... }
        True
        >>> query.resource_type
        'asn'
        """
        dict.__init__(self)
        for arg in args:
            parts = arg.split("=", 1)
            if len(parts) == 1:
                self["resource"] = parts[0]
            else:
                self[parts[0]] = parts[1]

        # Work out the resource type
        resource = self.get("resource")
        if resource:
            if "." in resource or "/" in resource or ":" in resource:
                self.resource_type = "ip"
            elif resource.lower().replace("as", "").isdigit():
                self.resource_type = "asn"
            else:
                self.resource_type = "unknown"
        else:
            self.resource_type = None
