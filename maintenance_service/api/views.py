from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from maintenance_service.api.serializers import WindowSerializer, OverrideSerializer
from maintenance_service.application.calendar_commands import (
    create_window,
    update_window,
    add_override,
)
from maintenance_service.application.calendar_queries import (
    availability,
    availability_snapshot,
)
from maintenance_service.api.request_validation import (
    safe_payload,
    window_create,
    window_patch,
    override_create,
    availability_params,
)
from maintenance_service.api.response_contracts import (
    window_response,
    availability_response,
)


def render(w, r):
    return window_response(w, r)


class WindowCollectionView(APIView):
    def post(self, request, organization, resource):
        payload = window_create(safe_payload(request.data))
        s = WindowSerializer(data=payload)
        s.is_valid(raise_exception=True)
        w, r = create_window(organization, resource, s.validated_data)
        return Response(render(w, r), status=status.HTTP_201_CREATED)


class WindowDetailView(APIView):
    def patch(self, request, organization, resource, window_id):
        payload = window_patch(safe_payload(request.data))
        s = WindowSerializer(data={**payload, "window_id": window_id}, partial=True)
        s.is_valid(raise_exception=True)
        w, r = update_window(organization, resource, window_id, s.validated_data)
        return Response(render(w, r))


class OverrideView(APIView):
    def post(self, request, organization, resource, window_id):
        payload = override_create(safe_payload(request.data))
        s = OverrideSerializer(data=payload)
        s.is_valid(raise_exception=True)
        w, r = add_override(organization, resource, window_id, s.validated_data)
        return Response(render(w, r), status=status.HTTP_201_CREATED)


class AvailabilityView(APIView):
    def get(self, request, organization, resource):
        return Response(
            availability_response(
                availability_snapshot(
                    organization, resource, availability_params(request.query_params)
                )
            )
        )
