from __future__ import division

from . import simple_table


def widget(api, query):
    data = api.get_data("routing-status", query, version=1)

    visibility = data["visibility"]["ris_peers_seeing"] / \
        data["visibility"]["total_ris_peers"]

    result = [
        ("routing-status", data["resource"]),
        ("visibility", "{0:.0%}    {1} of {2} full peers".format(
            visibility, data["visibility"]["ris_peers_seeing"],
            data["visibility"]["total_ris_peers"])),
    ]

    if data.get("first_seen"):
        result.append(("first-seen", data["first_seen"]["time"]))
    else:
        result.append(("first-seen", "never"))

    if "announced_v4_prefixes" in data:
        result.append(("announced-v4", "{announced_v4_prefixes} prefixes; "
            "{announced_v4_ips} IPs".format(**data)))
    if "announced_v6_prefixes" in data:
        result.append(("announced-v6", "{announced_v6_prefixes} prefixes; "
            "equivalent to {announced_v6_48s} /48{0}".format("s" if
            data["announced_v6_48s"] > 1 else "", **data)))
    if "observed_neighbours" in data:
        result.append((("bgp-neighbours", "{observed_neighbours}".format(
            **data))))

    get_table = lambda suggestions: simple_table((s["prefix"], "announced by",
        str(s["origin"])) for s in suggestions)

    for suggestion in get_table(data.get("less_specifics", [])):
        result.append(("less-specific", suggestion))

    for suggestion in get_table(data.get("more_specifics", [])):
        result.append(("more-specific", suggestion))


    return result
