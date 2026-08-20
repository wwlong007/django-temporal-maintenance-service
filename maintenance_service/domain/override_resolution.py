from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from .errors import InvalidSchedule


@dataclass(frozen=True)
class OverrideInstruction:
    action: str
    original_start: datetime
    start: datetime
    end: datetime
    sequence: int = 0

    def __post_init__(self):
        if self.action not in {"include", "exclude", "replace", "cancel"}:
            raise InvalidSchedule("override action is invalid")
        if self.end <= self.start:
            raise InvalidSchedule("override interval must be positive")


def ordered(instructions: Iterable[OverrideInstruction]):
    return tuple(
        sorted(
            instructions,
            key=lambda item: (item.original_start, item.sequence, item.action),
        )
    )


def resolve(base, instructions):
    values = {start: (start, end) for start, end in base}
    for instruction in ordered(instructions):
        if instruction.action in {"exclude", "cancel"}:
            values.pop(instruction.original_start, None)
        elif instruction.action == "replace":
            values.pop(instruction.original_start, None)
            values[instruction.start] = (instruction.start, instruction.end)
        else:
            values[instruction.start] = (instruction.start, instruction.end)
    return tuple(values[key] for key in sorted(values))


def conflicts(instructions):
    grouped = {}
    for item in instructions:
        grouped.setdefault(item.original_start, []).append(item)
    return {key: tuple(value) for key, value in grouped.items() if len(value) > 1}


def latest_per_original(instructions):
    result = {}
    for item in ordered(instructions):
        result[item.original_start] = item
    return tuple(result[key] for key in sorted(result))


def coverage_delta(base, resolved):
    base_duration = sum((end - start).total_seconds() for start, end in base)
    resolved_duration = sum((end - start).total_seconds() for start, end in resolved)
    return resolved_duration - base_duration


def affected_starts(instructions):
    return tuple(sorted({item.original_start for item in instructions}))


def validate_instruction_payload(payload):
    required = {"action", "start", "end"}
    if not required <= set(payload):
        raise InvalidSchedule("override payload is incomplete")
    return payload
