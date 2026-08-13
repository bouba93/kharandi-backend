import re
import unicodedata


GUINEA_TRIGGERS = {
    "guinee", "guinea", "guineen", "guineenne", "conakry", "fouta", "fouta-djallon",
    "fouta-djalon", "basse-guinee", "moyenne-guinee", "haute-guinee",
    "guinee-forestiere", "boke", "faranah", "kankan", "kindia", "labe",
    "mamou", "nzerekore", "mont-nimba", "simandou", "soussou", "poular",
    "pular", "maninka", "malinke", "kpele", "kissi",
}


def _normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold().replace("’", "'")
    return re.sub(r"[^a-z0-9'-]+", " ", value).strip()


def should_search_guinea(message: str) -> bool:
    normalised = _normalise(message)
    padded = f" {normalised.replace(' ', '-')} "
    tokens = set(normalised.split())
    # Ne pas confondre la République de Guinée avec les deux pays homonymes.
    if ({"bissau", "equatoriale"} & tokens) and not (
        {"conakry", "guineen", "guineenne"} & tokens
        or normalised.split().count("guinee") > 1
    ):
        return False
    return bool(tokens & GUINEA_TRIGGERS) or any(
        trigger in padded for trigger in GUINEA_TRIGGERS if "-" in trigger
    )


def get_guinea_context(message: str, limit: int = 3) -> str:
    """Retourne les fiches les plus pertinentes sans dépendance vectorielle."""
    from .models import GuineaKnowledgeEntry

    normalised_message = _normalise(message)
    message_tokens = set(normalised_message.split())
    entries = GuineaKnowledgeEntry.objects.filter(is_active=True)[:100]
    ranked = []

    for entry in entries:
        score = 0
        title = _normalise(entry.title)
        content = _normalise(entry.content)
        keywords = [_normalise(keyword) for keyword in entry.keywords if keyword]

        for keyword in keywords:
            if keyword and keyword in normalised_message:
                score += 8 + min(len(keyword.split()), 3)
        score += len(message_tokens & set(title.split())) * 3
        score += len(message_tokens & set(content.split()))

        # Une question générale sur la Guinée privilégie les fiches prioritaires.
        if "guinee" in message_tokens:
            score += max(entry.priority, 1) / 25
        if score:
            ranked.append((score, entry.priority, entry))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [item[2] for item in ranked[: max(1, min(limit, 5))]]
    if not selected:
        return ""

    parts = []
    for entry in selected:
        parts.append(
            f"=== {entry.title} [{entry.get_category_display()}] ===\n"
            f"{entry.content[:1200]}\n"
            f"Source : {entry.source_title}\n"
            f"URL : {entry.source_url}\n"
            f"Fiche vérifiée le : {entry.verified_on.isoformat()}"
        )
    return "\n\n[CONNAISSANCES GUINÉE — BASE KHARANDI]\n" + "\n\n".join(parts) + "\n"
