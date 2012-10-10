def widget(api, query):
    data = api.get_data("prefix-overview", query)

    result = [
        ("prefix-overview", data["resource"]),
    ]
    if data["block"] and data["block"]["resources"]:
        result.append(("part-of", data["block"]["resources"] + ": " +
            data["block"]["name"]))
    if data["announced"]:
        asn = "%s [%s]" % (data["asn"], data["holder"])
        result.append(("announced", "yes"))
        result.append(("announced-by", asn))
    else:
        result.append(("announced", "no"))
    return result
