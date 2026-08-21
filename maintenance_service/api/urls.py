from django.urls import path

from .views import (
    AvailabilityView,
    WindowBatchView,
    WindowCollectionView,
    WindowDetailView,
)


urlpatterns = [
    path(
        "organizations/<str:organization>/resources/<str:resource>/maintenance-windows",
        WindowCollectionView.as_view(),
    ),
    path(
        "organizations/<str:organization>/resources/<str:resource>/maintenance-windows/batch",
        WindowBatchView.as_view(),
    ),
    path(
        "organizations/<str:organization>/resources/<str:resource>/maintenance-windows/<str:window_id>",
        WindowDetailView.as_view(),
    ),
    path(
        "organizations/<str:organization>/resources/<str:resource>/availability",
        AvailabilityView.as_view(),
    ),
]
