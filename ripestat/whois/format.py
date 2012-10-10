class WhoisSerializer(object):
    """
    Simple serializer that outputs in to a pseudo whois format.
    """

    def get_items(self, native, parent=None):
        """
        Return a list of key, value pairs suitable for whois-style output.
        """
        items = []
        if isinstance(native, dict) or isinstance(native, list) and parent is \
                None:
            if isinstance(native, dict):
                native = native.items()
            for record in native:
                if isinstance(record, (basestring, type(None))):
                    if record:
                        items.append("% " + record)
                    else:
                        items.append("")
                else:
                    key, value = record
                    if isinstance(parent, basestring):
                        key = ".".join((str(parent), key))
                    items.extend(self.get_items(value, parent=key))
        elif isinstance(native, list):
            non_empty = 0
            for item in native:
                if parent:
                    key = "{0}.{1}".format(parent, non_empty)
                else:
                    key = str(non_empty)
                more_items = self.get_items(item, parent=key)
                if more_items:
                    items.extend(more_items)
                    non_empty += 1
        else:
            if parent:
                native = unicode(native).rstrip()
                if parent:
                    items = [(parent, native)]
                else:
                    items = [native]

        return items

    def dumps(self, native, plugin=None, **kwargs):  #pylint: disable-msg=W0613
        """
        Dump 'native' to a whois-style string.
        """
        if plugin and "resource" in native:
            native[plugin] = native["resource"]
            del native["resource"]
        elif plugin:
            native[plugin] = ""

        parts = self.get_items(native)
        longest_key = 0
        for part in parts:
            if not isinstance(part, basestring):
                longest_key = max(longest_key, len(part[0] or ""))
        lines = []
        for part in parts:
            if isinstance(part, basestring):
                lines.append(part)
            else:
                lines.append((part[0] + ":").ljust(longest_key + 4) + part[1])
        return "\n".join(lines)
