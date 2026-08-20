def merge_occurrences(base, rdates, exdates, overrides):
    values = {item[0]: item for item in base}
    for item in rdates:
        values[item[0]] = item
    for override in overrides:
        start = override["original_start"]
        if override["action"] == "exclude" or override["action"] == "cancel":
            values.pop(start, None)
        elif override["action"] == "replace":
            values.pop(start, None)
            values[override["start"]] = (override["start"], override["end"])
        elif override["action"] == "include":
            values[override["start"]] = (override["start"], override["end"])
    for start in exdates:
        values.pop(start, None)
    return sorted(values.values(), key=lambda item: item[0])
