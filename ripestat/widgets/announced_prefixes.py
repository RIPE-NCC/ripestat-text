def widget(api, query):
    data = api.get_data("announced-prefixes", query, version=1)

    result = [
        ("announced-prefixes", data["resource"]),
    ]
    for prefix in sorted(data["prefixes"], key=lambda x: x["prefix"]):
        result.append(("prefix", prefix["prefix"]))
    return data, result
