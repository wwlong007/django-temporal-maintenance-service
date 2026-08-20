from .interval_algebra import Interval


def effective_intervals(occurrences):
    result = []
    for current in sorted(occurrences, key=lambda x: (-x[2], x[0], x[1])):
        remaining = [Interval(current[0], current[1])]
        for kept in result:
            next_remaining = []
            for piece in remaining:
                if not piece.overlaps(kept[0]):
                    next_remaining.append(piece)
                    continue
                if piece.start < kept[0].start:
                    next_remaining.append(Interval(piece.start, kept[0].start))
                if kept[0].end < piece.end:
                    next_remaining.append(Interval(kept[0].end, piece.end))
            remaining = next_remaining
        result.extend((piece, current[2], current[3]) for piece in remaining)
    return sorted(result, key=lambda x: x[0].start)
