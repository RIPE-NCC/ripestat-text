def widget(api, query):
    data = api.get_data("as-overview", query, version=0)

    result = [
        ("as-overview", data["resource"]),
        ("announced", "yes" if data["announced"] else "no"),
    ]
    if data["holder"]:
        result.append(("description", data["holder"]))
    if data["block"]:
        result.append(("part-of", data["block"]["resources"] + ": " +
            data["block"]["name"]))

    return result
