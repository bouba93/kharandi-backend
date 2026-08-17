"""core/utils.py — Enveloppes de réponse et gestion centralisée des erreurs.

Règle d'or de cette API : **une réponse d'erreur est toujours du JSON**.
Aucun endpoint sous /api/ ne doit jamais renvoyer une page HTML Django ou
Nginx à un client. Ce module fournit les briques côté DRF ; le filet de
sécurité pour les erreurs qui échappent à DRF (DisallowedHost, 404 hors
routeur, 500 non capturé) est dans core/middleware.py (ErreursJsonMiddleware).
"""
import json
import logging
import uuid

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404, StreamingHttpResponse
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

# Exceptions que DRF sait déjà traduire en réponse HTTP correcte.
# À ré-émettre systématiquement (`raise`) dans un `except` large, sinon un
# `except Exception` transforme un 400 de validation légitime en faux 500.
API_EXCEPTIONS = (
    APIException,
    Http404,
    DjangoPermissionDenied,
    DjangoValidationError,
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
        message = first_error or "Une erreur est survenue."
        # DRF renvoie ce message en anglais : on le traduit sans masquer le
        # détail technique (position de l'erreur), utile au débogage frontend.
        if message.startswith("JSON parse error"):
            message = (
                "Le corps de la requête n'est pas du JSON valide. "
                + message.replace("JSON parse error - ", "Détail : ", 1)
            )
        response.data = {
            "success": False,
            "message": message,
            "errors": response.data,
            "status": response.status_code,
            # Alias de lecture pour les clients qui attendent error/details.
            "error": message,
            "details": response.data,
        }
    return response


def success_response(data=None, message="Succès", status=200):
    return Response({"success": True, "message": message, "data": data}, status=status)


def error_response(message="Erreur", errors=None, status=400, extra=None):
    """Réponse d'erreur JSON normalisée.

    Le corps expose volontairement deux jeux de clés équivalents :
      - `message` / `errors`  → format historique de l'API Kharandi ;
      - `error`   / `details` → alias, pour un client qui lit ces noms.
    Aucune rupture de compatibilité : ce sont des clés ajoutées, pas renommées.
    """
    corps = {
        "success": False,
        "message": message,
        "errors": errors,
        "error": message,
        "details": errors,
    }
    if extra:
        corps.update(extra)
    return Response(corps, status=status)


def internal_error_response(view_logger, contexte, message="Erreur interne du serveur.", status=500):
    """Journalise la trace complète et ne renvoie au client qu'une référence.

    Le détail technique d'une exception (`str(exc)`) ne doit jamais être
    renvoyé au client : il fuite des noms de tables, des chemins et parfois
    des données. On journalise tout côté serveur avec une référence courte,
    et le client ne reçoit que cette référence à communiquer au support.
    """
    reference = uuid.uuid4().hex[:12]
    view_logger.exception("[%s] %s", reference, contexte)
    return error_response(
        message,
        errors={"incident": reference},
        status=status,
        extra={"incident": reference},
    )


def sse_error_response(message, code="error", status=200, extra=None):
    """Erreur renvoyée dans le flux SSE, jamais en HTML ni en JSON classique.

    Utilisée par les endpoints `text/event-stream` : le client parse toujours
    des évènements `data: {...}`, y compris en cas d'échec. Le code HTTP réel
    est conservé (400, 429, 503…) pour que les outils de monitoring et les
    clients qui le lisent restent corrects — `fetch()` donne accès au corps
    même sur un 4xx.
    """
    charge = {"type": "error", "code": code, "message": message}
    if extra:
        charge.update(extra)

    def flux():
        yield f"data: {json.dumps(charge, ensure_ascii=False)}\n\n"

    response = StreamingHttpResponse(
        flux(), content_type="text/event-stream", status=status
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def client_attend_sse(request) -> bool:
    """Le client demande-t-il explicitement un flux SSE ?"""
    accept = (request.headers.get("Accept") or "").lower()
    return "text/event-stream" in accept
