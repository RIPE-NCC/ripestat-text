"""
Widget that renders either Prefix Overview or ASN Overview depending on the
given resource.
"""
from . import prefix_overview, as_overview


def widget(api, query):
    if query.resource_type == "asn":
        return as_overview.widget(api, query)
    elif query.resource_type == "ip":
        return prefix_overview.widget(api, query)
    else:
        return [
            "This widget supports ASN and IP resources"
        ]
