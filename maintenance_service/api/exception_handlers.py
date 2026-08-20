from rest_framework.views import exception_handler
from rest_framework.response import Response
from maintenance_service.domain.errors import DomainError


def api_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc)}, status=exc.status_code)
    response = exception_handler(exc, context)
    return response or Response({"detail": "request failed"}, status=500)
