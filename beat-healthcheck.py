#!/usr/bin/env python
"""
beat-healthcheck.py — Sonde de santé du conteneur Celery Beat
─────────────────────────────────────────────────────────────
Celery Beat n'expose ni port HTTP ni `inspect ping` (contrairement au worker) :
il faut donc une sonde spécifique.

Un Beat qui plante est peu dangereux — Docker le redémarre. Le vrai risque est
un Beat VIVANT MAIS BLOQUÉ : le conteneur paraît sain alors qu'aucune
réconciliation de paiement ne tourne plus. Des clients paieraient sans jamais
recevoir leur abonnement, en silence.

Deux vérifications LOCALES, sans dépendance réseau :

  1. le processus `celery beat` tourne bien dans ce conteneur ;
  2. le fichier d'état du planificateur a été écrit récemment — Beat le
     synchronise après chaque émission de tâche, et une tâche est planifiée
     chaque minute.

Le contrôle est volontairement local : une panne de Redis ou de PostgreSQL ne
doit pas faire passer Beat en `unhealthy`, sinon la vraie cause serait masquée.

Codes de sortie : 0 = sain, 1 = défaillant.
"""
import os
import sys
import time

ETAT_DIR = os.environ.get("BEAT_STATE_DIR", "/app/beat")
FICHIER_PLANNING = os.environ.get(
    "BEAT_SCHEDULE_FILE", os.path.join(ETAT_DIR, "celerybeat-schedule")
)
# Une tâche est planifiée chaque minute ; 10 minutes sans écriture signalent un
# blocage réel, sans être déclenché par un simple ralentissement.
AGE_MAX = int(os.environ.get("BEAT_HEALTH_MAX_AGE", "600"))


def echec(message):
    print(f"beat unhealthy: {message}", file=sys.stderr)
    sys.exit(1)


def processus_beat_actif() -> bool:
    """
    Parcourt /proc à la recherche du processus Beat (aucune dépendance externe :
    pgrep et ps ne sont pas garantis dans l'image python:3.12-slim).

    La comparaison porte sur les ARGUMENTS EXACTS, pas sur une sous-chaîne :
    sinon ce script de contrôle (« beat-healthcheck.py ») se détecterait
    lui-même et le conteneur paraîtrait toujours sain.
    """
    mon_pid = str(os.getpid())
    for entree in os.listdir("/proc"):
        if not entree.isdigit() or entree == mon_pid:
            continue
        try:
            with open(f"/proc/{entree}/cmdline", "rb") as f:
                brut = f.read()
        except (OSError, IOError):
            continue
        args = [a for a in brut.decode("utf-8", "replace").split("\x00") if a]
        if not args:
            continue
        # Attendu : « celery -A kharandi_backend beat --loglevel=info … »
        if "beat" in args and any(
            a == "celery" or a.endswith("/celery") for a in args
        ):
            return True
    return False


def main():
    if not processus_beat_actif():
        echec("le processus « celery beat » est introuvable dans le conteneur.")

    # Le planificateur peut utiliser un suffixe (.db, .dat, .dir, .bak) selon
    # l'implémentation de shelve : on retient le fichier le plus récent.
    candidats = [FICHIER_PLANNING] + [
        FICHIER_PLANNING + suffixe for suffixe in (".db", ".dat", ".dir", ".bak")
    ]
    horodatages = []
    for chemin in candidats:
        try:
            horodatages.append(os.path.getmtime(chemin))
        except OSError:
            continue

    if not horodatages:
        echec(
            f"aucun fichier d'état du planificateur trouvé ({FICHIER_PLANNING}). "
            "Beat vient peut-être de démarrer : vérifier après le start_period."
        )

    age = time.time() - max(horodatages)
    if age > AGE_MAX:
        echec(
            f"le planificateur n'a rien écrit depuis {int(age)} s "
            f"(seuil {AGE_MAX} s) : Beat est probablement bloqué. "
            "La réconciliation des paiements ne tourne plus."
        )

    print(f"beat healthy: dernière synchronisation il y a {int(age)} s")
    sys.exit(0)


if __name__ == "__main__":
    main()
