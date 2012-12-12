def widget(api, query):
    data = api.get_data("prefix-overview", query, version=1)

    result = [
        ("prefix-overview", data["resource"]),
    ]
    if data["block"] and data["block"]["resources"]:
        result.append(("part-of", data["block"]["resources"] + ": " +
            data["block"]["name"]))
    if data["announced"]:
	asns = []
	for asn_obj in data["asns"]:
	    asns.append("AS%s [%s]" % (asn_obj["asn"], asn_obj["holder"]))
        result.append(("announced", "yes"))
        result.append(("announced-by", ",".join(asns)))
    else:
        result.append(("announced", "no"))
    return data, result
