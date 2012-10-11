from fnmatch import fnmatch
from optparse import OptionParser, OptionGroup
from string import Formatter  # pylint: disable-msg=W0402
import logging
import re
from Queue import Queue
import threading

from ripestat import widgets
from ripestat.api import StatAPI, json
from ripestat.whois.format import WhoisSerializer


class QueryArgs(dict):
    __slots__ = "resource_type"


class Stat(object):
    """
    Class encapsulating the core functionality of RIPEstat text clients.
    """
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="count",
        help="set output level info (-v) or debug (-vv)")

    widget_group = OptionGroup(parser, "Widget Options")
    widget_group.add_option("-w", "--widgets", help="a comma separated list of "
        "widgets and @widget-groups to include in the output")
    widget_group.add_option("-l", "--list-widgets", action="store_true", help=
        "output the available widgets and @widget-groups")
    parser.add_option_group(widget_group)

    data_group = OptionGroup(parser, "Data API Options")
    data_group.add_option("-d", "--data-call", help=
        "get the raw response from a data call")
    data_group.add_option("--list-data-calls", help="output the available "
        "data calls", action="store_true")
    data_group.add_option("--explain-data-call", help="print help and "
        "methodology for a data call")
    data_group.add_option("-m", "--include-metadata", action="store_true",
        help="include the metadata in the data response instead of printing "
        "data to stdout and messages to stderr")
    data_group.add_option("-a", "--abbreviate-data", action="store_true", help=
        "abbreviate the response to get an idea of the structure")
    data_group.add_option("-s", "--select", help="select particular data item"
        " element(s) using dot notation, possibly using * globs -- e.g. "
        "'backward_refs.*.primary.key'")
    data_group.add_option("-t", "--template", help="render the response using "
        "Python 3 string formatting -- e.g. "
        "'{primary.key} = {primary.value}'")
    parser.add_option_group(data_group)

    def __init__(self, callback, base_url, token=None, parser=None,
            caller_id="core"):
        logging.basicConfig()
        self.logger = logging.getLogger("ripestat")

        self.output = callback

        self.caller_id = caller_id
        self.api = StatAPI(base_url=base_url, token=token, caller_id=caller_id)

        if parser:
            self.parser = parser

    @staticmethod
    def parse_args(args):
        """
        Convert positional key=value arguments to a Python dict.
        """
        query = QueryArgs()
        for arg in args:
            parts = arg.split("=", 1)
            if len(parts) == 1:
                query["resource"] = parts[0]
            else:
                query[parts[0]] = parts[1]

        resource = query.get("resource")
        if resource:
            if "." in resource or "/" in resource or ":" in resource:
                query.resource_type = "ip"
            elif resource.lower().replace("as", "").isdigit():
                query.resource_type = "asn"
            else:
                query.resource_type = "unknown"
        else:
            query.resource_type = None

        return query

    def get_plugin(self, query):
        """
        Decide which plugin to use based on the type of the given resource.
        """
        resource = query.get("resource", "")
        if resource.isalnum():
            return "as-overview"
        elif resource:
            return "prefix-overview"
        else:
            self.logger.error("No resource specified: "
                "can't guess which plugin to use")

    def output(self, line):
        raise NotImplementedError()

    class UsageError(Exception):
        """
        This is raised when the user has supplied funny parameters and might
        need to be reminded of the usage.
        """

    class OtherError(Exception):
        """
        This is raised when there is an error that won't be helped by displaying
        the usage help.
        """

    def main(self, args):
        """
        Process the command line from the user and print a response to stdout.
        """
        options, args = self.parser.parse_args(args)

        if options.list_widgets:
            return self.list_widgets()
        elif options.list_data_calls:
            return self.list_data_calls()
        elif options.explain_data_call:
            return self.explain_data_call(options.explain_data_call)

        if options.verbose == 1:
            self.logger.setLevel(logging.INFO)
        elif options.verbose and options.verbose >= 2:
            self.logger.setLevel(logging.DEBUG)

        query = self.parse_args(args)

        if options.data_call and options.widgets:
            raise self.UsageError(
                "--data-call and --widgets are conflicting options")
        elif options.data_call:
            self.api.caller_id = "%s/data-call" % self.caller_id
            return self.output_data(options.data_call, query,
                include_metadata=options.include_metadata,
                abbreviate=options.abbreviate_data, select=options.select,
                template=options.template)
        else:
            widget_names = self.get_widgets(options.widgets,
                query.resource_type)
            if widget_names:
                self.api.caller_id = "%s/widgets" % self.caller_id
                return self.output_widgets(widget_names, query)
            else:
                raise self.UsageError

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
                    raise self.OtherError("Unknown group: %s" % widget)
                final_list.extend(group_widgets)
            else:
                final_list.append(widget)
        return final_list

    def output_widgets(self, widget_names, query):
        """
        Carry out queries for the given resource and display results for the
        specified widgets.
        """
        lines = []

        if "resource" in query:
            lines.append("Results for '%s'" % query["resource"])
            lines.append("You can see graphical visualizations at "
                "https://stat.ripe.net/" + query["resource"])
        lines.append("")

        threads = []
        results_q = Queue()
        for widget_name in widget_names:
            widget = widgets.get_widget(widget_name)
            def exec_widget(widget, widget_name):
                try:
                    result = widget(self.api, query)
                except StatAPI.Error as exc:
                    result = exc
                results_q.put((widget_name, result))
            closure = lambda w=widget, n=widget_name: exec_widget(w, n)
            thread = threading.Thread(target=closure)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        try:
            for thread in threads:
                while thread.isAlive():
                    thread.join(0.01)
        except KeyboardInterrupt:
            return

        results = dict(results_q.queue)

        first = True
        for widget_name in widget_names:
            if first:
                first = False
            else:
                lines.append("")
            if isinstance(results[widget_name], Exception):
                message = unicode(results[widget_name])
                if not message:
                    message = "There was an error rendering this widget."
                lines.append(u"%s: %s" % (widget_name, message))
            else:
                lines.extend(results[widget_name])

        output = WhoisSerializer().dumps(lines)
        self.output(output)

        return 0

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
