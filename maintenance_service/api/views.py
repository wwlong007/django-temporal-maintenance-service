from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance_service.application.batches import commit_batch
from maintenance_service.application.commands import create_window, patch_window
from maintenance_service.application.queries import availability

from .serializers import (
    AvailabilitySerializer,
    WindowBatchSerializer,
    WindowCreateSerializer,
    WindowPatchSerializer,
)


class WindowCollectionView(APIView):
    def post(self, request, organization, resource):
        serializer = WindowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            create_window(organization, resource, serializer.validated_data),
            status=status.HTTP_201_CREATED,
        )


class WindowDetailView(APIView):
    def patch(self, request, organization, resource, window_id):
        serializer = WindowPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            patch_window(
                organization, resource, window_id, serializer.validated_data
            )
        )


class WindowBatchView(APIView):
    def post(self, request, organization, resource):
        serializer = WindowBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            commit_batch(
                organization, resource, serializer.validated_data["operations"]
            ),
            status=status.HTTP_201_CREATED,
        )


class AvailabilityView(APIView):
    def get(self, request, organization, resource):
        data = {
            "from_": request.query_params.get("from"),
            "to": request.query_params.get("to"),
        }
        if "revision" in request.query_params:
            data["revision"] = request.query_params["revision"]
        serializer = AvailabilitySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(
            availability(organization, resource, serializer.validated_data)
        )
