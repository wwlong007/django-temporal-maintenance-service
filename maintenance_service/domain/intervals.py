def partition(start, end, intervals):
    points = {start, end}
    clipped = []
    for item_start, item_end, priority, source in intervals:
        left = max(start, item_start)
        right = min(end, item_end)
        if left < right:
            clipped.append((left, right, priority, source))
            points.update((left, right))
    ordered = sorted(points)
    pieces = []
    for left, right in zip(ordered, ordered[1:]):
        covering = [item for item in clipped if item[0] <= left and item[1] >= right]
        if covering:
            winner = max(covering, key=lambda item: item[2])
            piece = {
                "start": left,
                "end": right,
                "maintenance": True,
                "available": False,
                "source_window_id": winner[3],
            }
        else:
            piece = {
                "start": left,
                "end": right,
                "maintenance": False,
                "available": True,
            }
        if pieces and _same_value(pieces[-1], piece):
            pieces[-1]["end"] = right
        else:
            pieces.append(piece)
    return pieces


def _same_value(left, right):
    return (
        left["maintenance"] == right["maintenance"]
        and left.get("source_window_id") == right.get("source_window_id")
        and left["end"] == right["start"]
    )
