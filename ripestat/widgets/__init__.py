from functools import partial


GROUPS = {
    "at-a-glance": {
        "widgets": [
            {
                "name": "as-overview",
                "resource-types": ["asn"]
            },
            {
                "name": "prefix-overview",
                "resource-types": ["ip"]
            },
            {
                "name": "geoloc",
                "resource-types": ["ip", "asn"]
            },
            {
                "name": "object-browser",
                "resource-types": ["ip", "asn"]
            },
            {
                "name": "routing-status",
                "resource-types": ["ip", "asn"]
            }
        ]
    }
}


def get_group_widgets(group_name, resource_type):
    group_name = group_name.lower()
    widgets = []
    for widget in GROUPS.get(group_name, {}).get("widgets", []):
        if resource_type in widget["resource-types"]:
            widgets.append(widget["name"])
    return widgets


def get_widget(widget_name):
    sanitized_name = widget_name.replace("-", "_").replace(" ", "_")
    try:
        module = __import__("ripestat.widgets.%s" % sanitized_name,
            fromlist=True)
    except ImportError:
        return partial(default_widget, widget_name)
    return module.widget


def get_widget_list():
    rows = []
    for group in GROUPS.values():
        for widget in group["widgets"]:
            row = widget["name"], ",".join(widget["resource-types"])
            rows.append(row)
    rows.sort()
    return simple_table(rows)


def get_widget_groups():
    for group, definition in GROUPS.items():
        yield group, definition["widgets"]


def default_widget(widget_name, api, query):
    data = api.get_data(widget_name, query)
    items = [
        "'%s' doesn't have a command-line widget yet. Below is a direct translation of the data response." % widget_name,
        "You can contribute a widget at https://stat.ripe.net/cli/",
    ]
    title = widget_name
    resource = data.get("resource")
    if resource:
        items.append((title, data["resource"]))
        del data["resource"]
    items.extend(sorted(data.items()))
    return items


def simple_table(rows):
    # Calculate the column widths
    widths = None
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        if widths is None:
            widths = [len(col) for col in row]
        else:
            widths = [max(width, len(col)) for (width, col) in zip(widths, row)]

    # Yield the rows
    for row in rows:
        if isinstance(row, (list, tuple)):
            line = "  ".join(p.ljust(width) for (width, p) in zip(widths, row))
            yield line
        else:
            yield row
