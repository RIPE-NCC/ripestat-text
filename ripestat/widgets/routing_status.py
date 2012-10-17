from __future__ import division


def widget(api, query):
    data = api.get_data("routing-status", query, version=1)

    visibility = data["visibility"]["ris_peers_seeing"] / \
        data["visibility"]["total_ris_peers"]

    result = [
        ("routing-status", data["resource"]),
        ("visibility", "{0:.0%}    {1} of {2} full peers".format(
            visibility, data["visibility"]["ris_peers_seeing"],
            data["visibility"]["total_ris_peers"])),
        ("first-seen", data["first_seen"]["time"]),
        ("announced-v4", "{announced_v4_prefixes} prefixes; {announced_v4_ips}"
            " IPs".format(**data)),
        ("announced-v6", "{announced_v6_prefixes} prefixes; equivalent to "
            "{announced_v6_48s} /48{0}".format("s" if data["announced_v6_48s"]
            > 1 else "", **data)),
        ("bgp-neighbours", "{observed_neighbours}".format(**data)),
    ]

    return result
