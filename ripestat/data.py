"""
Contains the data API processing functionality.
"""
import logging
from fnmatch import fnmatch
from string import Formatter  # pylint: disable-msg=W0402
import re
from abc import ABCMeta

from ripestat.api import json


class DataProcessor(object):
    """
    Mixin class that has methods for dealing with calling, processing and
    outputting the RIPEstat Data API.
    """
    __metaclass__ = ABCMeta

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

        if select is not None:
            select = select.split(".")
            data = self.select(data, select)
            if not template and not abbreviate:
                template = "{0}"

        if abbreviate:
            data = self.abbreviate_lists(data)

        if template is not None:
            formatter = DataFormatter()
            output = formatter.format_data(template.decode("utf-8"), data)
        else:
            output = json.dumps(data, indent=4)
            if abbreviate:
                output = output.replace('"' + self.ellipsis_marker + '"',
                    "...")

        self.output(output)

        if not include_metadata:
            if response.meta.get("cached", False):
                self.logger.log(logging.INFO, "This response was cached")

    ellipsis_marker = "...abbreviate_lists_ELLIPSIS..."
    def abbreviate_lists(self, data, insert_ellipsis=True, top_level=True):
        """
        Recursively remove all but the first item in lists.
        """
        abbreviated = False
        if isinstance(data, list) and data:
            data = [self.abbreviate_lists(data[0], insert_ellipsis,
                False)]
            if insert_ellipsis:
                data.append(self.ellipsis_marker)
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


