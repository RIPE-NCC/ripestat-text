import datetime


def widget(api, query):
    import pdb; pdb.set_trace()
    if "start_time" not in query:
        query["start_time"] = datetime.datetime.now() - \
            datetime.timedelta(days=3)
    data = api.get_data("routing-history", query, version=1)

    result = [
        ("routing-history", data["resource"])
    ]

    for prefixes_for_origin in data["by_origin"]:
        origin = prefixes_for_origin["origin"]
        if data["resource"] != origin:
            result.append(("origin", origin))
        for prefix in prefixes_for_origin["prefixes"]:
            timeline = prefix["timelines"][-1]
            result.append(("prefix", "%s from %s to %s" % (prefix["prefix"],
                timeline["starttime"], timeline["endtime"])))

    return result
