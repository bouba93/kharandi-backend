import logging
from rest_framework.response import Response
from rest_framework.views import exception_handler
logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        first_error = None
        errors = response.data
        if isinstance(errors, dict):
            for key, val in errors.items():
                if isinstance(val, list) and val: first_error = str(val[0]); break
                elif isinstance(val, str): first_error = val; break
        elif isinstance(errors, list) and errors:
            first_error = str(errors[0])
        response.data = {
            "success": False, "message": first_error or "Une erreur est survenue.",
            "errors": response.data, "status": response.status_code,
        }
    return response

def success_response(data=None, message="Succès", status=200):
    return Response({"success": True, "message": message, "data": data}, status=status)

def error_response(message="Erreur", errors=None, status=400):
    return Response({"success": False, "message": message, "errors": errors}, status=status)
