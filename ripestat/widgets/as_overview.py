def widget(api, query):
    data = api.get_data("as-overview", query, version=1)

    result = [
        ("as-overview", data["resource"]),
        ("announcing-prefixes", "yes" if data["announced"] else "no"),
    ]
    if data["holder"]:
        result.append(("description", data["holder"]))
    if data["block"]:
        result.append(("part-of", data["block"]["resources"] + ": " +
                      data["block"]["name"]))

    return data, result
