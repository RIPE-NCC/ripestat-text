from . import simple_table


def widget(api, query):
    data = api.get_data("routing-history", query, version=1)

    result = [
        ("routing-history", data["resource"])
    ]

    routes = []
    for prefixes_for_origin in data["by_origin"]:
        origin = prefixes_for_origin["origin"]
        for prefix in sorted(prefixes_for_origin["prefixes"], key=lambda x:
                x["timelines"][-1]["endtime"], reverse=True):
            timeline = prefix["timelines"][-1]
            routes.append((origin, prefix["prefix"], timeline["starttime"],
                "to", timeline["endtime"]))
    for value in simple_table(routes):
        result.append(("route", value))

    return data, result
