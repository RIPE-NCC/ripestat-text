from __future__ import division

from . import simple_table


def widget(api, query):
    data = api.get_data("routing-status", query, version=2)

    vis_strs = {}
    for protocol in "v4", "v6":
        vis_data = data["visibility"][protocol]
        vis_ratio = vis_data["ris_peers_seeing"] / \
            (vis_data["total_ris_peers"] or 1)
        vis_str = "{0:.0%} of {1} peers".format(vis_ratio,
            vis_data["total_ris_peers"])
        vis_strs[protocol] = vis_str


    result = [
        ("routing-status", data["resource"]),
        ("ipv4-visibility", vis_strs["v4"]),
        ("ipv6-visibility", vis_strs["v6"])
    ]

    if data.get("first_seen"):
        first_seen = data["first_seen"]["time"]
        if first_seen < "2001-01-01T":
            first_seen = "before Jan 2001"
        result.append(("first-seen", first_seen))
    else:
        result.append(("first-seen", "never"))

    if "announced_space" in data:
        result.append(("announced-v4", "{announced_space[v4][prefixes]} "
            "prefixes; {announced_space[v4][ips]} IPs".format(**data)))
        result.append(("announced-v6", "{announced_space[v6][prefixes]} "
            "prefixes; {announced_space[v6][48s]} /48 equivalents".format(**data)))
    if "observed_neighbours" in data:
        result.append((("bgp-neighbours", "{observed_neighbours}".format(
            **data))))

    get_table = lambda suggestions: simple_table((s["prefix"], "announced by",
        str(s["origin"])) for s in suggestions)

    for suggestion in get_table(data.get("less_specifics", [])):
        result.append(("less-specific", suggestion))

    for suggestion in get_table(data.get("more_specifics", [])):
        result.append(("more-specific", suggestion))


    return data, result
