def widget(api, query):
    data = api.get_data("object-relationships", query, version=0)

    result = [
        ("object-browser", data["resource"]),
    ]

    if "database" in data:
        result.append(("database", data["database"]))

    if len(data["objects"]) == 1:
        result.append(("type", data["objects"][0]["type"]))
        for field in data["objects"][0]["fields"]:
            if field["value"] == data["resource"]:
                continue
            result.append((field["key"], field["value"]))
        result.append(("num-versions", data["num_versions"]))
        result.append("The ref-by- fields show which objects refer to %s" %
            data["resource"])
        for obj in data["backward_refs"]:
            result.append(("ref-by-%s" % obj["primary"]["key"],
                obj["primary"]["value"]))
    else:
        for suggestion in data.get("suggestions", []):
            result.append(("suggestion", suggestion["primary"]["value"]))
    return data, result
