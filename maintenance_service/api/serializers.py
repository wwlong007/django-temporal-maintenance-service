from rest_framework import serializers


class WindowSerializer(serializers.Serializer):
    window_id = serializers.CharField(required=False)
    calendar = serializers.CharField(required=False, default="default")
    timezone = serializers.CharField(required=False)
    rule = serializers.DictField(required=False)
    exceptions = serializers.DictField(required=False)
    priority = serializers.IntegerField(required=False)
    effective_from = serializers.DateTimeField(required=False)
    version = serializers.IntegerField(required=False)


class OverrideSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=["include", "exclude", "replace", "cancel"]
    )
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    original_start = serializers.DateTimeField(required=False)
    version = serializers.IntegerField()
