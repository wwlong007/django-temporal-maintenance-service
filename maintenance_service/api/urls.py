from django.urls import path
from .views import (
    WindowCollectionView,
    WindowDetailView,
    OverrideView,
    AvailabilityView,
)

urlpatterns = [
    path(
        "organizations/<str:organization>/resources/<str:resource>/maintenance-windows",
        WindowCollectionView.as_view(),
    ),
    path(
        "organizations/<str:organization>/resources/<str:resource>/maintenance-windows/<str:window_id>",
        WindowDetailView.as_view(),
    ),
    path(
        "organizations/<str:organization>/resources/<str:resource>/maintenance-windows/<str:window_id>/overrides",
        OverrideView.as_view(),
    ),
    path(
        "organizations/<str:organization>/resources/<str:resource>/availability",
        AvailabilityView.as_view(),
    ),
]
