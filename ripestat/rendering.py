"""
Contains the text widget rendering functionality.
"""
from abc import ABCMeta
import logging
import threading

from ripestat import widgets
from ripestat.api import StatAPI
from ripestat.parser import UserError


LOG = logging.getLogger(__name__)


class WidgetRenderer(object):
    """
    Mixin class that has methods for dealing with rendering text widgets.
    """
    __metaclass__ = ABCMeta
    # Time in seconds before giving up on showing a particular widget in order
    order_timeout = 0.2
    # Width of the key fields on the left in unordered mode
    unordered_key_width = 20

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
                    raise UserError("No such widget group: {0}".format(
                        widget))
                final_list.extend(group_widgets)
            else:
                final_list.append(widget)
        return final_list

    def output_widgets(self, widgets_spec, query, include_metadata=False,
            preserve_order=False):
        """
        Carry out queries for the given resource and display results for the
        specified widgets.
        """
        widget_names = self.get_widgets(widgets_spec, query.resource_type)
        if not widget_names:
            if "resource" in query:
                raise UserError("No widgets match the given resource "
                    "type.")
            else:
                raise UserError(show_help=True)

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
                logging.exception(exc)

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
