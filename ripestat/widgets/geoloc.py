from . import simple_table


def widget(api, query):
    data = api.get_data("geoloc", query, version=1)

    result = [
        ("geoloc", data["resource"]),
    ]

    loc_rows = []
    for location in sorted(data["locations"], key=lambda l:
            l["covered_percentage"], reverse=True):
        loc_row = []
        percent = location["covered_percentage"]
        if percent >= 0.1:
            loc_row.append("%4.1f%%" % percent)
        else:
            loc_row.append("<0.1%")
        if location["city"] and location["country"]:
            loc_row.append("%s, %s" % (location["city"], location["country"]))
        elif location["city"] or location["country"]:
            loc_row.append((location["city"] or location["country"]))
        loc_rows.append(loc_row)
    for loc_str in simple_table(loc_rows):
        result.append(("location", loc_str))

    return result
