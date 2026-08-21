from datetime import datetime

from rest_framework import serializers


def has_offset(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


class WindowCreateSerializer(serializers.Serializer):
    window_id = serializers.CharField()
    effective_from = serializers.DateTimeField()
    timezone = serializers.CharField()
    rule = serializers.DictField()
    priority = serializers.IntegerField()
    active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if not has_offset(self.initial_data.get("effective_from")):
            raise serializers.ValidationError("effective_from must include an offset")
        return attrs


class WindowPatchSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    effective_from = serializers.DateTimeField()
    timezone = serializers.CharField(required=False)
    rule = serializers.DictField(required=False)
    priority = serializers.IntegerField(required=False)
    active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not has_offset(self.initial_data.get("effective_from")):
            raise serializers.ValidationError("effective_from must include an offset")
        if not any(key in attrs for key in ("timezone", "rule", "priority", "active")):
            raise serializers.ValidationError("a state change is required")
        return attrs


class AvailabilitySerializer(serializers.Serializer):
    from_ = serializers.DateTimeField(source="from")
    to = serializers.DateTimeField()
    revision = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs):
        start = attrs["from"]
        end = attrs["to"]
        if start.tzinfo is None or end.tzinfo is None:
            raise serializers.ValidationError("range timestamps require offsets")
        if end <= start:
            raise serializers.ValidationError("to must be after from")
        if (end - start).total_seconds() > 366 * 86400:
            raise serializers.ValidationError("range is too long")
        return attrs
