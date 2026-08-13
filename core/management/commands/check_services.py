"""
check_services — Vérifie que les clés des fournisseurs externes fonctionnent.

Teste réellement chaque service (pas seulement la présence de la variable) :
    Nimba SMS   → authentification sur le compte
    LengoPay    → autorisation de la clé de licence
    OpenRouter  → validité de la clé et crédit restant

Usage sur le serveur :
    docker compose exec api python manage.py check_services
    docker compose exec api python manage.py check_services --sms +224620000000
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

OK   = "\033[0;32m[OK]\033[0m   "
WARN = "\033[1;33m[!]\033[0m    "
FAIL = "\033[0;31m[X]\033[0m    "
TIMEOUT = 20


class Command(BaseCommand):
    help = "Vérifie les clés des fournisseurs externes (Nimba, LengoPay, OpenRouter)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sms",
            metavar="NUMERO",
            help="Envoie un vrai SMS de test au numéro indiqué (format +224XXXXXXXXX).",
        )

    # ── Utilitaires ──────────────────────────────────────────────────────────
    def ok(self, msg):   self.stdout.write(OK + msg)
    def warn(self, msg): self.stdout.write(WARN + msg)
    def fail(self, msg): self.stdout.write(FAIL + msg)

    def masked(self, value):
        if not value:
            return "(vide)"
        return f"{value[:4]}…{value[-4:]} ({len(value)} caractères)"

    # ── Nimba SMS ────────────────────────────────────────────────────────────
    def check_nimba(self, test_number=None):
        self.stdout.write(self.style.MIGRATE_HEADING("\nNimba SMS — codes OTP"))
        sid   = getattr(settings, "NIMBA_ACCOUNT_SID", "")
        token = getattr(settings, "NIMBA_AUTH_TOKEN", "")

        if not sid or not token:
            self.fail("Clés absentes. Aucun SMS ne partira : personne ne pourra "
                      "créer de compte ni se connecter.")
            return False

        self.stdout.write(f"       SID   : {self.masked(sid)}")
        self.stdout.write(f"       Token : {self.masked(token)}")

        try:
            import base64
            auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
            r = requests.get(
                "https://api.nimbasms.com/v1/accounts",
                headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
                timeout=TIMEOUT,
            )
        except Exception as exc:
            self.fail(f"Connexion impossible à Nimba : {exc}")
            return False

        if r.status_code == 200:
            data = r.json() if r.content else {}
            balance = data.get("balance", data.get("sms_balance", "inconnu"))
            self.ok(f"Authentification réussie. Solde SMS : {balance}")
        elif r.status_code in (401, 403):
            self.fail("Identifiants refusés (HTTP %d). Vérifiez SID et token." % r.status_code)
            return False
        else:
            self.warn(f"Réponse inattendue (HTTP {r.status_code}) : {r.text[:200]}")

        if test_number:
            self.stdout.write(f"       Envoi d'un SMS de test à {test_number}…")
            try:
                from notifications.tasks import send_otp_sms
                res = send_otp_sms(test_number)
                if res.get("success"):
                    self.ok("SMS envoyé. Vérifiez le téléphone.")
                else:
                    self.fail(f"Échec de l'envoi : {res}")
                    return False
            except Exception as exc:
                self.fail(f"Erreur pendant l'envoi : {exc}")
                return False
        return True

    # ── LengoPay ─────────────────────────────────────────────────────────────
    def check_lengopay(self):
        self.stdout.write(self.style.MIGRATE_HEADING("\nLengoPay — paiements Orange Money / MTN"))
        site = getattr(settings, "LENGOPAY_SITE_ID", "")
        lic  = getattr(settings, "LENGOPAY_LICENSE_KEY", "")

        if not site or not lic:
            self.fail("Clés absentes. Aucun paiement ne pourra être initié.")
            return False

        self.stdout.write(f"       Site ID  : {self.masked(site)}")
        self.stdout.write(f"       Licence  : {self.masked(lic)}")
        self.stdout.write(f"       Callback : {settings.LENGOPAY_CALLBACK_URL}")

        if "onrender.com" in settings.LENGOPAY_CALLBACK_URL:
            self.fail("Le callback pointe encore vers Render. Corrigez "
                      "LENGOPAY_CALLBACK_URL dans le .env, sinon les paiements "
                      "ne seront jamais confirmés.")

        if "localhost" in settings.LENGOPAY_CALLBACK_URL or "127.0.0.1" in settings.LENGOPAY_CALLBACK_URL:
            self.fail("Le callback pointe vers localhost : LengoPay ne pourra pas le joindre.")

        try:
            r = requests.post(
                "https://portal.lengopay.com/api/v1/payments",
                headers={
                    "Authorization": f"Basic {lic}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "websiteid":    site,
                    "amount":       1000,
                    "currency":     settings.LENGOPAY_CURRENCY,
                    "country":      settings.LENGOPAY_COUNTRY,
                    "callback_url": settings.LENGOPAY_CALLBACK_URL,
                },
                timeout=TIMEOUT,
            )
        except Exception as exc:
            self.fail(f"Connexion impossible à LengoPay : {exc}")
            return False

        if r.status_code in (401, 403):
            self.fail("Clé de licence refusée (HTTP %d)." % r.status_code)
            return False

        # LengoPay renvoie une page HTML d'erreur 500 lorsque les identifiants
        # sont invalides, au lieu d'un 401. On exige donc une réponse JSON
        # contenant une URL de paiement pour conclure que la clé fonctionne.
        try:
            data = r.json()
        except ValueError:
            self.fail(
                f"Réponse non JSON (HTTP {r.status_code}) : identifiants "
                "probablement invalides. Vérifiez le Site ID et la clé de licence."
            )
            return False

        if r.status_code == 200 and data.get("payment_url"):
            self.ok("Clé valide : une URL de paiement de test a été générée.")
            self.warn("Cette transaction de test reste non réglée, sans effet.")
        else:
            self.fail(f"Réponse inattendue (HTTP {r.status_code}) : {str(data)[:200]}")
            return False

        # Vérification du chemin de confirmation des callbacks
        pay_id = str(data.get("pay_id", "")).strip()
        if pay_id:
            from payments.views import _lengopay_status
            state, _ = _lengopay_status(pay_id)
            if state is None:
                self.fail(
                    "La vérification du statut a échoué. Sans elle, aucun paiement "
                    "ne sera confirmé automatiquement. Demandez à LengoPay l'URL "
                    "de consultation d'un paiement et renseignez-la dans "
                    "LENGOPAY_STATUS_URL (avec {pay_id} comme emplacement)."
                )
                return False
            self.ok(f"Vérification serveur à serveur opérationnelle (statut : {state}).")

        if not getattr(settings, "LENGOPAY_WEBHOOK_SECRET", ""):
            self.warn("Aucun secret webhook : les callbacks sont confirmés par "
                      "appel direct à LengoPay. C'est le fonctionnement prévu.")
        return True

    # ── OpenRouter ───────────────────────────────────────────────────────────
    def check_openrouter(self):
        self.stdout.write(self.style.MIGRATE_HEADING("\nOpenRouter — assistant Karamo"))
        key = getattr(settings, "OPENROUTER_API_KEY", "")

        if not key:
            self.fail("Clé absente. Karamo renverra une erreur 503 à chaque question.")
            return False

        self.stdout.write(f"       Clé : {self.masked(key)}")
        if not key.startswith("sk-or-"):
            self.warn("Format inhabituel : une clé OpenRouter commence par « sk-or- ».")

        try:
            r = requests.get(
                "https://openrouter.ai/api/v1/key",
                headers={"Authorization": f"Bearer {key}"},
                timeout=TIMEOUT,
            )
        except Exception as exc:
            self.fail(f"Connexion impossible à OpenRouter : {exc}")
            return False

        if r.status_code == 200:
            d = r.json().get("data", {})
            limit, usage = d.get("limit"), d.get("usage")
            if limit is None:
                self.ok(f"Clé valide. Usage : {usage} (aucun plafond).")
            else:
                reste = round(float(limit) - float(usage or 0), 4)
                self.ok(f"Clé valide. Crédit restant : {reste} sur {limit}.")
                if reste <= 0:
                    self.fail("Crédit épuisé : Karamo ne répondra plus.")
                    return False
            return True

        if r.status_code == 401:
            self.fail("Clé refusée (HTTP 401). Elle est invalide ou révoquée.")
        else:
            self.warn(f"Réponse HTTP {r.status_code} : {r.text[:200]}")
        return False

    # ── Point d'entrée ───────────────────────────────────────────────────────
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "Vérification des fournisseurs externes Kharandi"))

        results = {
            "Nimba SMS":  self.check_nimba(options.get("sms")),
            "LengoPay":   self.check_lengopay(),
            "OpenRouter": self.check_openrouter(),
        }

        self.stdout.write(self.style.MIGRATE_HEADING("\nRésumé"))
        for name, ok in results.items():
            (self.ok if ok else self.fail)(name)

        broken = [n for n, ok in results.items() if not ok]
        self.stdout.write("")
        if broken:
            self.stdout.write(self.style.ERROR(
                f"À corriger dans /opt/kharandi/.env : {', '.join(broken)}. "
                "Puis : docker compose restart api"))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Tous les fournisseurs répondent correctement."))
