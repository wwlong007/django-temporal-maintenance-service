from django.urls import path
from .views import (
    WindowCollectionView,
    WindowDetailView,
    OverrideView,
    AvailabilityView,
    MaintenancePolicyCollectionView,
    MaintenancePolicyDetailView,
    MaintenancePlanCollectionView,
    MaintenanceImpactView,
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
    path(
        "organizations/<str:organization>/maintenance-policies",
        MaintenancePolicyCollectionView.as_view(),
    ),
    path(
        "organizations/<str:organization>/maintenance-policies/<str:policy_id>",
        MaintenancePolicyDetailView.as_view(),
    ),
    path(
        "organizations/<str:organization>/maintenance-plans",
        MaintenancePlanCollectionView.as_view(),
    ),
    path(
        "organizations/<str:organization>/maintenance-impact",
        MaintenanceImpactView.as_view(),
    ),
]
