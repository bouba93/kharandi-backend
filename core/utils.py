import logging
import secrets

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404

from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# Exceptions que DRF sait déjà transformer en réponses HTTP propres.
# Elles ne doivent surtout pas être capturées comme des erreurs internes.
API_EXCEPTIONS = (
    APIException,
    Http404,
    PermissionDenied,
    DjangoValidationError,
    DRFValidationError,
)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        first_error = None
        errors = response.data

        if isinstance(errors, dict):
            for key, val in errors.items():
                if isinstance(val, list) and val:
                    first_error = str(val[0])
                    break
                elif isinstance(val, str):
                    first_error = val
                    break

        elif isinstance(errors, list) and errors:
            first_error = str(errors[0])

        response.data = {
            "success": False,
            "message": first_error or "Une erreur est survenue.",
            "errors": response.data,
            "status": response.status_code,
        }

    return response


def success_response(data=None, message="Succès", status=200):
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status,
    )


def error_response(message="Erreur", errors=None, status=400):
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors,
        },
        status=status,
    )


def internal_error_response(logger_instance, contexte, message="Une erreur interne est survenue."):
    """
    Journalise la vraie exception côté serveur et ne l'expose jamais au client.
    """

    incident = secrets.token_hex(6)

    logger_instance.exception(
        "ERREUR INTERNE [%s] — %s",
        incident,
        contexte,
    )

    return error_response(
        message,
        errors={"incident": incident},
        status=500,
    )
