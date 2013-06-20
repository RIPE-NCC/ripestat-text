"""
Tools for parsing user/client input.
"""
from optparse import OptionParser, OptionGroup, make_option


class BaseParser(OptionParser):
    """
    Option parser that knows about all of the options available for
    ripestat-text.

    This can be subclassed to add more options or change the behaviour.
    """
    # General options
    standard_option_list = [
        make_option("-v", "--verbose", action="count",
                    help="set output level info (-v) or debug (-vv)"),
        make_option("--version", action="store_true",
                    help="print the ripestat-text version"),
        make_option("--help", "-h", action="store_true",
                    help="show this help text"),
        make_option("-m", "--include-metadata", action="store_true",
                    help="include metadata in the responses"),
    ]

    # Widget options
    widget_option_list = [
        make_option("-w", "--widgets", help="a comma separated list of "
                    "widgets and @widget-groups to include in the output"),
        make_option("-l", "--list-widgets", action="store_true",
                    help="output the available widgets and @widget-groups"),
        make_option("-o", "--preserve-order", action="store_true",
                    help="force the widgets to be returned in the same "
                    "order even if some are faster than others"),
    ]

    # Data options
    data_option_list = [
        make_option("-d", "--data-call", help=
                    "get the raw response from a data call"),
        make_option("--list-data-calls", help="output the available "
                    "data calls", action="store_true"),
        make_option("--explain-data-call", help="print help and "
                    "methodology for a data call"),
        make_option("-a", "--abbreviate-data", action="store_true", help=
                    "abbreviate the response to get an idea of the "
                    "structure"),
        make_option("-s", "--select", help="select particular data item"
                    " element(s) using dot notation, possibly using * globs "
                    "-- e.g. 'backward_refs.*.primary.key'"),
        make_option("-t", "--template", help="render the response using "
                    "Python 3 string formatting -- e.g. "
                    "'{primary.key} = {primary.value}'"),
    ]

    def __init__(self, *args, **kwargs):
        kwargs["add_help_option"] = False
        OptionParser.__init__(self, *args, **kwargs)
        widget_group = OptionGroup(self, "Widget Options")

        for option in self.widget_option_list:
            widget_group.add_option(option)
        self.add_option_group(widget_group)

        data_group = OptionGroup(self, "Data API Options")
        for option in self.data_option_list:
            data_group.add_option(option)
        self.add_option_group(data_group)


class UserError(Exception):
    """
    This is raised when the user has supplied funny parameters and may or may
    not need to be reminded of the usage.
    """
    def __init__(self, *args, **kwargs):
        self.show_help = kwargs.pop("show_help", False)
        Exception.__init__(self, *args, **kwargs)
