"""
Module containing the main parsing/dispatching functionality for ripestat-text.

The 'whois' and 'cli' interfaces both use this module.
"""
from fnmatch import fnmatch
from optparse import OptionParser, OptionGroup, make_option
from string import Formatter  # pylint: disable-msg=W0402
import logging
import re
import threading

from ripestat import widgets, __version__
from ripestat.api import StatAPI, json
from ripestat.whois import WhoisSerializer


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


class StatCoreParser(OptionParser):
    """
    Option parser that knows about all of the options available for StatCore.

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
        make_option("-w", "--widgets", help="a comma separated list "
            "of widgets and @widget-groups to include in the output"),
        make_option("-l", "--list-widgets", action="store_true", help=
            "output the available widgets and @widget-groups"),
        make_option("-o", "--preserve-order", action="store_true", help=
            "force the widgets to be returned in the same order even if some "
                "are faster than others"),
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
            "abbreviate the response to get an idea of the structure"),
        make_option("-s", "--select", help="select particular data item"
            " element(s) using dot notation, possibly using * globs -- e.g. "
            "'backward_refs.*.primary.key'"),
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


class StatCore(object):
    """
    Class encapsulating the core functionality of ripestat-text.

    Calling classes can specify their own parser with more options. These
    custom parsers must however be based on StatCore.parser.
    """
    # Time in seconds before giving up on showing a particular widget in order
    order_timeout = 0.2
    # Width of the key fields on the left in unordered mode
    unordered_key_width = 20

    def __init__(self, callback, api, parser=None):
        logging.basicConfig()
        self.logger = logging.getLogger("ripestat")

        # This function is called whenever something needs to be output to the
        # user.
        self.output = callback

        self.api = api
        self.caller_id = self.api.caller_id

        if parser:
            self.parser = parser
        else:
            self.parser = StatCoreParser()

        self.serializer = WhoisSerializer()

    def main(self, args):
        """
        Process the command line from the user and print a response to stdout.

        This method calls self._main() so that it can catch UsageWithHelp and
        UsageWithoutHelp.
        """
        options, args = self.parser.parse_args(args)

        try:
            return self._main(options, args)
        except UsageWithHelp as exc:
            if exc.message:
                self.output(exc.message)
                self.output("")
            self.output(self.parser.format_option_help())
            return 1
        except UsageWithoutHelp as exc:
            self.output(exc.message)
            return 2

    def _main(self, options, args):
        """
        Internal method for responding to a command line.

        May raise UsageWithHelp or UsageWithoutHelp.
        """
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
            raise UsageWithHelp(
                "--data-call and --widgets are conflicting options")
        elif options.data_call:
            self.api.caller_id = "%s/data-call" % self.caller_id
            return self.output_data(options.data_call, query,
                include_metadata=options.include_metadata,
                abbreviate=options.abbreviate_data, select=options.select,
                template=options.template)
        else:
            self.api.caller_id = "%s/widgets" % self.caller_id
            return self.output_widgets(options.widgets, query,
                include_metadata=options.include_metadata,
                preserve_order=options.preserve_order)

    def show_version(self):
        """
        Output the public ripestat-text version label.
        """
        self.output(unicode(__version__))

    ################################################
    # Methods for working with ripestat-text widgets
    ################################################

    def list_widgets(self):
        """
        Output a list of available widgets.
        """
        self.output("% widgets")
        for widget in widgets.get_widget_list():
            self.output(widget)
        self.output("")
        self.output("% widget groups")
        for widget_group, widget_defs in widgets.get_widget_groups():
            line = "@%s    " % widget_group + ",".join(w["name"] for w in
                widget_defs)
            self.output(line)

    def output_widgets(self, widgets_spec, query, include_metadata=False,
            preserve_order=False):
        """
        Carry out queries for the given resource and display results for the
        specified widgets.
        """
        widget_names = self.get_widgets(widgets_spec, query.resource_type)
        if not widget_names:
            if "resource" in query:
                raise UsageWithoutHelp("No widgets match the given resource "
                    "type.")
            else:
                raise UsageWithHelp()

        header = []
        if "resource" in query:
            header.append("Results for '%s'" % query["resource"])
            header.append("You can see graphical visualizations at "
                "https://stat.ripe.net/" + query["resource"])
            self.output_whois(header)

        # Execute each widget in parallel
        threads = []
        for widget_name in widget_names:
            result = []
            def closure(widget_name=widget_name, result=result):
                """
                Execute a widget and put its result in a list of its own.
                """
                lines = self.exec_widget(widget_name, query, include_metadata)
                result.extend(lines)
            thread = threading.Thread(target=closure)
            thread.daemon = True  # makes the thread die with the controller
            threads.append((thread, result))

        for thread, result in threads:
            thread.start()

        # Output the widgets
        try:
            if preserve_order:
                # Render each widget in order, using a dynamically calculated
                # key width
                results = []
                for thread, result in threads:
                    thread.join(None)
                    results.append("")
                    results.extend(result)
                self.output_whois(results)
            else:
                # Render the widgets as they become available (loosely in
                # order) using a constant minimum key width
                while threads:
                    for thread_info in threads[:]:
                        thread, result = thread_info
                        thread.join(self.order_timeout)
                        if not thread.isAlive():
                            self.output("")
                            self.output_whois(result,
                                min_key_width=self.unordered_key_width)
                            threads.remove(thread_info)
        except KeyboardInterrupt:
            return

        return 0

    def exec_widget(self, widget_name, query, include_metadata):
        """
        Execute a widget and return a list of output lines.
        """
        widget = widgets.get_widget(widget_name)
        try:
            result = widget(self.api, query)
        except StatAPI.Error as exc:
            result = exc
        except Exception as exc:
            if isinstance(exc, StatAPI.Error):
                message = unicode(exc)
            else:
                message = "There was an error rendering this widget."

            result = [
                u"%{0}: {1}".format(widget_name, message)
            ]
        else:
            response, result = result
            time_str = ""
            if response is None:
                response = {}
            if "query_time" in response:
                time_str += response["query_time"]
            else:
                if "query_starttime" in response:
                    time_str = response["query_starttime"]
                if "query_endtime" in response:
                    if "query_starttime" in response:
                        time_str += " to "
                    else:
                        time_str += "since "
                    time_str += response["query_endtime"]
            if time_str:
                result.append(("query-time", time_str))
            if include_metadata:
                for key in response.meta:
                    result.append(("meta-" + key, response.meta[key]))
        return result

    def output_whois(self, lines, **kwargs):
        """
        Output the given lines in a whois style format.
        """
        output = self.serializer.dumps(lines, **kwargs)
        self.output(output)

    def get_widgets(self, widget_names, resource_type):
        """
        Resolve a comma separated list of widgets and @widget-groups to a
        native list of widget names.
        """
        initial_list = widget_names.split(",") if widget_names else []
        if not initial_list:
            initial_list.append("@at-a-glance")

        final_list = []
        for widget in initial_list:
            if widget.startswith("@"):
                group_widgets = widgets.get_group_widgets(widget[1:],
                    resource_type)
                if group_widgets is None:
                    raise UsageWithoutHelp("No such widget group: {0}".format(
                        widget))
                final_list.extend(group_widgets)
            else:
                final_list.append(widget)
        return final_list


    ################################################
    # Methods for working directly with the Data API 
    ################################################

    def list_data_calls(self):
        """
        Output a list of available data calls.
        """
        response = self.api.get_response("list.json")
        native = json.loads(response)

        for plugin in sorted(p["slug"] for p in native):
            self.output(plugin)

    def explain_data_call(self, data_call):
        """
        Output the methodology for a given data call.
        """
        response = self.api.get_response("%s/meta/methodology" % data_call)
        native = json.loads(response)
        self.output(data_call)
        self.output("-" * len(data_call))
        self.output(native["methodology"])

    def output_data(self, data_call, query, include_metadata=False,
            abbreviate=False, select=None, template=None):
        """
        Return data for a single data call, possibly including some
        line-oriented maninpulation.
        """
        response = data = self.api.get_data(data_call, query)

        if include_metadata:
            data = response.meta
            data["data"] = response
        else:
            for message in response.meta["messages"]:
                level = getattr(logging, message[0].upper())
                self.logger.log(level, message[1])

        if abbreviate:
            data = self.abbreviate_lists(data)

        if select is not None or template is not None:
            if select:
                select = select.split(".")
            else:
                select = []
            data = self.select(data, select)
            formatter = DataFormatter()

            if template is None:
                template = "{0}"
            else:
                template = template.decode("utf-8")
            output = formatter.format_data(template, data)
        else:
            output = json.dumps(data, indent=4)

        self.output(output)

        if not include_metadata:
            if response.meta.get("cached", False):
                self.logger.log(logging.INFO, "This response was cached")

    def abbreviate_lists(self, data, insert_ellipsis=True, top_level=True):
        """
        Recursively remove all but the first item in lists.
        """
        abbreviated = False
        if isinstance(data, list) and data:
            data = [self.abbreviate_lists(data[0], insert_ellipsis,
                False)]
            if insert_ellipsis:
                data.append("...")
        elif isinstance(data, dict):
            return dict((k, self.abbreviate_lists(data[k], insert_ellipsis,
                False)) for k in data)
        else:
            return data
        if top_level and abbreviated and not insert_ellipsis:
            self.logger.warn("Lists have been abbreviated to one item.")
        return data

    def select(self, data, path):
        """
        Select one or more data items, optionally using fnmatch (*) wildcards.
        """
        while path:
            member = path.pop(0)
            if "*" in member:
                actual_data = data
                if isinstance(actual_data, dict):
                    actual_data = [actual_data[k] for k in actual_data if
                        fnmatch(k, member)]
                data = GlobList()

                for actual_member in actual_data:
                    more = self.select(actual_member, path[:])
                    if isinstance(more, GlobList):
                        data.extend(more)
                    else:
                        data.append(more)
                return data
            else:
                try:
                    member = int(member)
                except ValueError:
                    pass
                data = data[member]
        return data


class UsageWithHelp(Exception):
    """
    This is raised when the user has supplied funny parameters and might
    need to be reminded of the usage.
    """


class UsageWithoutHelp(Exception):
    """
    This is raised when there is an error that won't be helped by displaying
    the usage help.
    """


class GlobList(list):
    """
    List subclass that indicates that a sequence is formed from glob expression
    and can be merged by further globbing.
    """


class DataFormatter(Formatter):
    """
    String formatter for processing the API responses according to user
    provided templates.
    """
    dot_re = re.compile(r"\.(\w+)")

    def get_field(self, field_name, args, kwargs):
        """
        Overidden API method that converts '.' usage to '[]' indexing.
        """
        field_name = self.dot_re.sub(r"[\1]", field_name)
        return Formatter.get_field(self, field_name, args, kwargs)

    def format_data(self, format_string, data):
        """
        Take a list or a dict and return a formatted string.
        """
        if isinstance(data, dict):
            # pylint: disable-msg=W0142
            return self.format(format_string, data, **data)
        elif isinstance(data, list):
            return "\n".join(self.format_data(format_string, obj) for obj in
                data)
        else:
            return self.format(format_string, data)
