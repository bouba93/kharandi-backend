from urllib.parse import urlparse

from rest_framework import serializers

# ─── Tolérance de format d'entrée pour Karamo ────────────────────────────────
#
# Le contrat officiel reste :  {"message": "...", "history": [{"role", "content"}]}
#
# Mais un client (web, mobile, futur SDK) peut légitimement nommer le champ
# autrement, ou modéliser ses messages de chat avec d'autres clés. Rejeter la
# requête avec un HTTP 400 dans ces cas-là est un échec inutile : la donnée
# nécessaire est présente, seul le nom du champ diffère. On normalise donc
# l'entrée AVANT validation, sans jamais relâcher les contrôles qui protègent
# réellement le service (champ obligatoire, longueur maximale, rôle « system »
# interdit côté client, historique borné).

# Alias acceptés pour le message courant, par ordre de priorité.
ALIAS_MESSAGE = ("message", "prompt", "question", "content", "text", "query", "input")

# Alias acceptés pour le contenu d'un message d'historique.
ALIAS_CONTENU = ("content", "text", "message", "value", "answer", "prompt")

# Alias acceptés pour le rôle d'un message d'historique.
ALIAS_ROLE = ("role", "author", "sender", "from", "type")

# Normalisation des rôles vers les deux seuls rôles acceptés par le modèle.
#
# « system » est volontairement ABSENT de cette table : le prompt système de
# Karamo est construit côté serveur (_build_messages). Laisser un client
# injecter un message `system` serait une faille d'injection de prompt. Ces
# entrées sont donc ignorées silencieusement plutôt que refusées.
CORRESPONDANCE_ROLES = {
    "user": "user",
    "utilisateur": "user",
    "human": "user",
    "humain": "user",
    "me": "user",
    "moi": "user",
    "client": "user",
    "assistant": "assistant",
    "bot": "assistant",
    "ai": "assistant",
    "ia": "assistant",
    "model": "assistant",
    "karamo": "assistant",
    "karamö": "assistant",
    "kharandi": "assistant",
}

ROLES_IGNORES = {"system", "système", "systeme", "developer", "tool", "function"}

# Nombre maximal de messages d'historique transmis au modèle.
# C'est une protection de coût (jetons facturés) : elle est CONSERVÉE, mais on
# tronque aux N messages les plus récents au lieu de renvoyer un 400.
# Un chat normal dépasse 10 messages en quelques échanges ; refuser la requête
# rendait Karamo inutilisable dès le 6e aller-retour.
HISTORIQUE_MAX = 10

# Longueur maximale d'un contenu d'historique. Tronquée, pas refusée.
CONTENU_MAX = 4000

# Longueur maximale du message courant. Refusée (contrôle d'abus volontaire) :
# tronquer silencieusement la question de l'utilisateur produirait une réponse
# fausse sans qu'il le sache.
MESSAGE_MAX = 4000


def _texte(valeur) -> str:
    """Convertit une valeur quelconque en texte exploitable, ou en chaîne vide."""
    if valeur is None or isinstance(valeur, (dict, list, tuple, set, bool)):
        return ""
    return str(valeur).strip()


def _extraire_contenu(element) -> str:
    """Récupère le texte d'un message d'historique, quelle que soit sa forme.

    Formes gérées : {"content": "..."}, {"text": "..."}, {"message": "..."},
    la forme OpenAI multimodale {"content": [{"type": "text", "text": "..."}]},
    et la chaîne brute "...".
    """
    if isinstance(element, str):
        return element.strip()
    if not isinstance(element, dict):
        return ""
    for cle in ALIAS_CONTENU:
        if cle not in element:
            continue
        brut = element[cle]
        # Forme multimodale OpenAI : liste de blocs {"type": "text", "text": ...}
        if isinstance(brut, list):
            morceaux = [
                _texte(bloc.get("text") or bloc.get("content"))
                for bloc in brut
                if isinstance(bloc, dict)
            ]
            texte = " ".join(m for m in morceaux if m).strip()
        else:
            texte = _texte(brut)
        if texte:
            return texte
    return ""


def _extraire_role(element, defaut="user"):
    """Normalise le rôle d'un message. Retourne None si le message doit être ignoré."""
    if isinstance(element, str):
        return defaut
    if not isinstance(element, dict):
        return None
    brut = ""
    for cle in ALIAS_ROLE:
        brut = _texte(element.get(cle)).lower()
        if brut:
            break
    if not brut:
        return defaut
    if brut in ROLES_IGNORES:
        return None
    return CORRESPONDANCE_ROLES.get(brut, defaut)


def normaliser_historique(brut) -> list:
    """Transforme un historique de forme quelconque en [{role, content}] valide.

    Ne lève jamais d'erreur : l'historique est du contexte d'agrément, il ne
    doit pas empêcher l'utilisateur de poser sa question.
    """
    if brut is None or brut == "":
        return []
    if isinstance(brut, dict):  # un client peut n'envoyer qu'un seul message
        brut = [brut]
    if not isinstance(brut, (list, tuple)):
        return []

    normalise = []
    for index, element in enumerate(brut):
        contenu = _extraire_contenu(element)
        if not contenu:
            continue  # message vide → ignoré, pas d'erreur
        if isinstance(element, dict):
            defaut = "user"
        else:
            # Une liste de chaînes brutes est lue en alternance user/assistant.
            defaut = "user" if index % 2 == 0 else "assistant"
        role = _extraire_role(element, defaut=defaut)
        if role is None:
            continue  # rôle système/outil → ignoré (anti-injection de prompt)
        normalise.append({"role": role, "content": contenu[:CONTENU_MAX]})

    # Protection de coût conservée : on garde les messages les plus récents.
    return normalise[-HISTORIQUE_MAX:]


def extraire_message(donnees: dict) -> str:
    """Trouve le message courant parmi les alias acceptés.

    Gère aussi le format OpenAI `{"messages": [...]}` : le dernier message
    de rôle utilisateur devient le message courant.
    """
    for cle in ALIAS_MESSAGE:
        texte = _texte(donnees.get(cle))
        if texte:
            return texte

    conversation = donnees.get("messages")
    if isinstance(conversation, (list, tuple)):
        for element in reversed(conversation):
            if _extraire_role(element, defaut="user") != "user":
                continue
            contenu = _extraire_contenu(element)
            if contenu:
                return contenu
    return ""


class HistoryMessageSerializer(serializers.Serializer):
    """Conservé pour compatibilité (schéma OpenAPI, autres appelants)."""

    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=CONTENU_MAX, trim_whitespace=True)


class AIAskSerializer(serializers.Serializer):
    """Valide une requête Karamo.

    Contrat de référence (inchangé, toujours accepté) :
        {"message": "Bonjour Karamo", "history": []}

    Formats additionnellement acceptés, normalisés vers ce contrat :
        {"prompt": "..."} / {"question": "..."} / {"content": "..."}
        {"text": "..."}   / {"query": "..."}    / {"input": "..."}
        {"messages": [{"role": "user", "content": "..."}]}   (format OpenAI)
        history avec rôles bot/ai/ia/model/karamo/human   → user | assistant
        history avec les clés text/message/value au lieu de content
        history sous forme de liste de chaînes
        history de plus de 10 messages  → tronqué aux 10 plus récents
        history absent, null, {} ou mal typé  → historique vide
    """

    message = serializers.CharField(
        max_length=MESSAGE_MAX,
        trim_whitespace=True,
        error_messages={
            "required": (
                "Le champ 'message' est obligatoire. Alias acceptés : "
                "prompt, question, content, text, query, input."
            ),
            "blank": "Le champ 'message' ne peut pas être vide.",
            "null": "Le champ 'message' ne peut pas être nul.",
            "max_length": (
                f"Le message est limité à {MESSAGE_MAX} caractères. "
                "Reformulez votre question plus brièvement."
            ),
        },
    )
    history = serializers.ListField(required=False, default=list)

    #: clés réellement reçues dans le corps ; renvoyées en cas d'erreur 400
    #: pour diagnostiquer un décalage de contrat sans avoir à deviner.
    cles_recues: list = []

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            self.cles_recues = []
            raise serializers.ValidationError(
                {"message": ["Le corps de la requête doit être un objet JSON."]}
            )

        self.cles_recues = sorted(str(cle) for cle in data.keys())

        normalise = dict(data)
        normalise["message"] = extraire_message(data)
        normalise["history"] = normaliser_historique(
            data.get("history", data.get("messages", data.get("historique")))
        )

        valide = super().to_internal_value(normalise)
        # `history` est déjà normalisé ; ListField le laisse passer tel quel.
        valide["history"] = normalise["history"]
        return valide


class AIImageAskSerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=2000,
        required=False,
        default="Explique et corrige ce document scolaire.",
        trim_whitespace=True,
    )
    image_url = serializers.CharField(
        max_length=2048,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )

    def validate_image_url(self, value):
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise serializers.ValidationError("L'URL de l'image doit être une URL HTTPS valide.")
        return value


class GenerateQCMSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=100, trim_whitespace=True)
    level = serializers.CharField(max_length=10, trim_whitespace=True)
    topic = serializers.CharField(max_length=200, trim_whitespace=True)
    difficulty = serializers.CharField(
        max_length=10,
        required=False,
        default="MOYEN",
    )

    def validate_difficulty(self, value):
        value = value.upper()
        if value not in {"FACILE", "MOYEN", "DIFFICILE"}:
            raise serializers.ValidationError("Difficulté invalide.")
        return value


class SubmitQCMSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.IntegerField(min_value=0, max_value=3),
        allow_empty=False,
    )
