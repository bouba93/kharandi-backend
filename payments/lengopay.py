"""
payments/lengopay.py — Client HTTP LengoPay (Cash In)
─────────────────────────────────────────────────────
Implémentation strictement conforme à la documentation officielle LengoPay,
section « Collect payments (Cash In) ».

1. Création d'un paiement
   POST {LENGOPAY_PAYMENT_URL}          (défaut …/api/v1/payments)
   Headers : Authorization: Basic {license key}
             Accept: application/json
             Content-Type: application/json
   Body    : websiteid, amount, currency, country,
             return_url, failure_url, callback_url
   Réponse : {"status": "Success", "pay_id": "...", "payment_url": "..."}

2. Vérification du statut d'une transaction
   POST {LENGOPAY_STATUS_URL}           (défaut …/api/v1/transaction/status)
   Headers : identiques
   Body    : {"pay_id": "...", "websiteid": "..."}
   Réponse : {"status": "...", "pay_id": "...", "date": "...", "amount": 1500}

3. Callback (notification)
   LengoPay envoie un POST JSON vers callback_url :
   {"pay_id", "status", "amount", "message", "Client"}
   → Aucune signature n'est prévue par le fournisseur.

Toutes les URL sont configurables par variables d'environnement afin de pouvoir
basculer vers le sandbox (https://sandbox.lengopay.com/api/v1) sans toucher au
code.
"""
import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Normalisation des libellés de statut renvoyés par LengoPay.
_SUCCESS_WORDS = {"SUCCESS", "SUCCESSFUL", "SUCCÈS", "COMPLETED", "COMPLETE", "PAID"}
_FAILED_WORDS = {
    "FAILED", "FAILURE", "ÉCHEC", "ECHEC", "CANCELLED", "CANCELED",
    "EXPIRED", "REJECTED", "DECLINED", "ERROR",
}
_PENDING_WORDS = {"PENDING", "INITIATED", "INITIATE", "PROCESSING", "IN_PROGRESS", "WAITING"}


def normalize_status(raw) -> str | None:
    """
    Traduit un statut LengoPay en SUCCESS / FAILED / PENDING.

    Retourne None si le libellé est inconnu : on préfère ne rien faire plutôt
    que d'interpréter à tort un statut non documenté.
    """
    if raw is None:
        return None
    value = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
    if not value:
        return None
    if value in _SUCCESS_WORDS:
        return "SUCCESS"
    if value in _FAILED_WORDS:
        return "FAILED"
    if value in _PENDING_WORDS:
        return "PENDING"
    return None


def extract_phone(payload: dict) -> str:
    """
    Récupère le numéro du payeur.

    La documentation liste l'exemple avec « Client » (C majuscule) ; certaines
    versions de l'API renvoient « client » ou « account » (Cash In v2). On
    accepte les trois graphies.
    """
    if not isinstance(payload, dict):
        return ""
    for key in ("Client", "client", "account", "phone", "msisdn"):
        value = payload.get(key)
        if value:
            return str(value).strip()[:20]
    return ""


def to_decimal(value):
    """Convertit un montant hétérogène (int, float, str) en Decimal, ou None."""
    if value is None:
        return None
    try:
        return Decimal(str(value).strip().replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _headers() -> dict:
    return {
        "Authorization": f"Basic {settings.LENGOPAY_LICENSE_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _unwrap(data):
    """Certaines réponses encapsulent le contenu utile dans « data »."""
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    return data


def create_payment(amount, currency, reference) -> dict:
    """
    Crée un paiement Cash In et retourne le lien de paiement.

    Retour : {"success": True, "pay_id": ..., "payment_url": ...}
          ou {"success": False, "error": ...}
    """
    if not settings.LENGOPAY_SITE_ID or not settings.LENGOPAY_LICENSE_KEY:
        logger.error("LengoPay non configuré : LENGOPAY_SITE_ID / LENGOPAY_LICENSE_KEY manquants.")
        return {"success": False, "error": "Passerelle de paiement non configurée."}

    montant = to_decimal(amount) or Decimal("0")
    body = {
        "websiteid": settings.LENGOPAY_SITE_ID,
        # GNF et XOF n'ont pas de sous-unité : on arrondit à l'entier.
        "amount": int(montant.to_integral_value()),
        "currency": (currency or settings.LENGOPAY_CURRENCY or "GNF").upper(),
        "country": settings.LENGOPAY_COUNTRY or "GN",
        "callback_url": settings.LENGOPAY_CALLBACK_URL,
        "return_url": f"{settings.FRONTEND_URL}/payment/success?ref={reference}",
        "failure_url": f"{settings.FRONTEND_URL}/payment/failure?ref={reference}",
    }

    try:
        resp = requests.post(
            settings.LENGOPAY_PAYMENT_URL,
            json=body,
            headers=_headers(),
            timeout=settings.LENGOPAY_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.error("LengoPay création injoignable [%s] : %s", reference, exc)
        return {"success": False, "error": f"Passerelle injoignable : {exc}"}

    try:
        data = resp.json()
    except ValueError:
        logger.error(
            "LengoPay création : réponse non JSON [HTTP %d] %r",
            resp.status_code, resp.text[:500],
        )
        return {"success": False, "error": f"Réponse invalide (HTTP {resp.status_code})."}

    logger.info("LengoPay création [%d] ref=%s : %s", resp.status_code, reference, data)
    payload = _unwrap(data)

    pay_id = str(payload.get("pay_id") or "").strip() if isinstance(payload, dict) else ""
    payment_url = str(payload.get("payment_url") or "").strip() if isinstance(payload, dict) else ""
    ok_status = str(payload.get("status") or "").strip().upper() if isinstance(payload, dict) else ""

    if resp.status_code == 200 and pay_id and payment_url and ok_status in {"SUCCESS", "INITIATED"}:
        return {"success": True, "pay_id": pay_id, "payment_url": payment_url}

    return {"success": False, "error": data}


def transaction_status(pay_id: str):
    """
    Confirmation serveur-à-serveur du statut réel d'un paiement.

    Conforme à la documentation : POST {LENGOPAY_STATUS_URL} avec le corps
    {"pay_id": ..., "websiteid": ...}.

    Retourne (statut normalisé, montant Decimal|None), ou (None, None) si la
    vérification n'aboutit pas (API injoignable, endpoint refusé, statut
    inconnu). L'appelant NE DOIT PAS interpréter None comme un échec de
    paiement.
    """
    pay_id = str(pay_id or "").strip()
    if not pay_id:
        return None, None
    if not settings.LENGOPAY_LICENSE_KEY:
        logger.warning("Vérification LengoPay impossible : clé de licence absente.")
        return None, None

    url = str(settings.LENGOPAY_STATUS_URL or "").strip()
    if not url:
        return None, None

    # Compatibilité ascendante : une ancienne configuration pouvait contenir un
    # gabarit « …/payments/{pay_id} ». Ce format n'existe pas dans la
    # documentation ; on le corrige silencieusement.
    if "{pay_id}" in url:
        logger.warning(
            "LENGOPAY_STATUS_URL utilise l'ancien gabarit {pay_id} ; "
            "bascule automatique sur %s/transaction/status.",
            settings.LENGOPAY_BASE_URL,
        )
        url = f"{settings.LENGOPAY_BASE_URL}/transaction/status"

    body = {"pay_id": pay_id, "websiteid": settings.LENGOPAY_SITE_ID}

    try:
        resp = requests.post(url, json=body, headers=_headers(), timeout=settings.LENGOPAY_TIMEOUT)
    except requests.RequestException as exc:
        logger.error("Vérification LengoPay injoignable [%s] : %s", pay_id, exc)
        return None, None

    if resp.status_code != 200:
        logger.warning(
            "Vérification LengoPay [%s] : HTTP %d — %r",
            pay_id, resp.status_code, resp.text[:300],
        )
        return None, None

    try:
        data = _unwrap(resp.json())
    except ValueError:
        logger.warning("Vérification LengoPay [%s] : réponse non JSON %r", pay_id, resp.text[:300])
        return None, None

    if not isinstance(data, dict):
        logger.warning("Vérification LengoPay [%s] : format inattendu %r", pay_id, data)
        return None, None

    state = normalize_status(data.get("status"))
    if state is None:
        logger.warning(
            "Statut LengoPay inconnu pour %s : %r (réponse complète : %s)",
            pay_id, data.get("status"), data,
        )
        return None, None

    return state, to_decimal(data.get("amount"))
