"""Fiches guinéennes initiales, sourcées et chargées par ``seed_data``."""

from datetime import date


VERIFIED_ON = date(2026, 7, 15)

GUINEA_KNOWLEDGE = [
    {
        "slug": "identite-et-geographie",
        "category": "GEOGRAPHY",
        "title": "Identité et situation géographique de la Guinée",
        "content": (
            "La République de Guinée est un pays côtier d’Afrique de l’Ouest. Sa capitale est "
            "Conakry et sa superficie est de 245 857 km². Elle possède une façade sur l’océan "
            "Atlantique et partage des frontières avec la Guinée-Bissau, le Sénégal, le Mali, "
            "la Côte d’Ivoire, le Liberia et la Sierra Leone. Il ne faut pas la confondre avec "
            "la Guinée-Bissau ni avec la Guinée équatoriale."
        ),
        "keywords": [
            "guinée", "conakry", "capitale", "superficie", "frontières", "afrique de l'ouest",
        ],
        "source_title": "Ministère de l’Environnement — Symboles et présentation du pays",
        "source_url": "https://medd.gov.gn/symboles/",
        "priority": 100,
    },
    {
        "slug": "quatre-regions-naturelles",
        "category": "GEOGRAPHY",
        "title": "Les quatre régions naturelles",
        "content": (
            "La Guinée comprend quatre régions naturelles : la Guinée Maritime ou Basse Guinée, "
            "zone côtière ; la Moyenne Guinée, dominée par le massif du Fouta-Djalon ; la Haute "
            "Guinée, région de savanes et du haut bassin du Niger ; et la Guinée Forestière, "
            "région montagneuse et forestière du Sud-Est où se trouve le mont Nimba. Ces régions "
            "naturelles ne doivent pas être confondues avec les régions administratives."
        ),
        "keywords": [
            "régions naturelles", "basse guinée", "guinée maritime", "moyenne guinée",
            "fouta djallon", "fouta-djalon", "haute guinée", "guinée forestière",
        ],
        "source_title": "Ministère de l’Environnement — Présentation des régions naturelles",
        "source_url": "https://medd.gov.gn/charte-de-la-transition/",
        "priority": 95,
    },
    {
        "slug": "decoupage-administratif",
        "category": "INSTITUTIONS",
        "title": "Découpage administratif",
        "content": (
            "L’Institut national de la statistique distingue quatre régions naturelles et huit "
            "régions administratives. Il recense 33 préfectures ainsi que les communes urbaines "
            "de Conakry. Les régions administratives sont Boké, Conakry, Faranah, Kankan, Kindia, "
            "Labé, Mamou et N’Zérékoré. Pour un chiffre administratif plus récent, Karamo doit "
            "vérifier la dernière publication officielle de l’INS."
        ),
        "keywords": [
            "régions administratives", "préfectures", "sous-préfectures", "boké", "faranah",
            "kankan", "kindia", "labé", "mamou", "nzérékoré", "n'zérékoré",
        ],
        "source_title": "Institut national de la statistique de Guinée",
        "source_url": "https://www.stat-guinee.org/",
        "priority": 90,
    },
    {
        "slug": "chateau-eau-afrique-ouest",
        "category": "ENVIRONMENT",
        "title": "Le château d’eau de l’Afrique de l’Ouest",
        "content": (
            "Le relief guinéen, en particulier le Fouta-Djalon, alimente plusieurs grands cours "
            "d’eau ouest-africains. Des bassins liés au Niger, au Sénégal et à la Gambie prennent "
            "leur source en Guinée. Cette fonction hydrographique explique le surnom de « château "
            "d’eau de l’Afrique de l’Ouest »."
        ),
        "keywords": [
            "fleuves", "niger", "sénégal", "gambie", "fouta", "château d'eau", "hydrographie",
        ],
        "source_title": "Stratégie nationale de réduction des risques de catastrophes 2024-2030",
        "source_url": "https://medd.gov.gn/file/2024/06/Strategie_SNRRC-2024_2030.pdf",
        "source_published_on": date(2024, 6, 1),
        "priority": 85,
    },
    {
        "slug": "langues-nationales",
        "category": "CULTURE",
        "title": "Français et langues nationales",
        "content": (
            "Le français est la langue officielle. Parmi les principales langues nationales "
            "figurent le poular ou pular, le maninka, le soussou, le kissi, le kpèlè et le toma "
            "ou lomagöi. Leur présence varie selon les régions et de nombreuses autres langues "
            "sont également parlées. Karamo doit respecter les différentes graphies et éviter "
            "d’associer automatiquement une langue à l’identité d’une personne."
        ),
        "keywords": [
            "langues", "français", "poular", "pular", "peul", "maninka", "malinké",
            "soussou", "susu", "kissi", "kpèlè", "guerzé", "toma", "lomagöi",
        ],
        "source_title": "INS — Annuaire statistique 2022",
        "source_url": (
            "https://www.stat-guinee.org/images/Documents/Publications/INS/annuelles/annuaire/"
            "Annuaire_Statistique_2022_VF_INS.pdf"
        ),
        "source_published_on": date(2022, 12, 31),
        "priority": 85,
    },
    {
        "slug": "independance-1958",
        "category": "HISTORY",
        "title": "Indépendance de la Guinée",
        "content": (
            "La Guinée a proclamé son indépendance le 2 octobre 1958 après la période coloniale "
            "française. Cette date est la fête nationale. Ahmed Sékou Touré a dirigé le pays au "
            "début de l’indépendance. Pour expliquer cette histoire, Karamo doit distinguer les "
            "faits établis des interprétations politiques."
        ),
        "keywords": [
            "indépendance", "2 octobre 1958", "sékou touré", "histoire", "colonisation",
        ],
        "source_title": "Ministère de l’Environnement — Politique nationale d’assainissement",
        "source_url": (
            "https://medd.gov.gn/file/2023/08/Politique-Nationale_Assainissement_Guinee_2010.pdf"
        ),
        "priority": 90,
    },
    {
        "slug": "examens-nationaux",
        "category": "EDUCATION",
        "title": "Examens nationaux du préuniversitaire",
        "content": (
            "Les trois grands examens scolaires nationaux présentés par le ministère sont le "
            "Certificat de fin d’études élémentaires (CEE), le Brevet d’études du premier cycle "
            "(BEPC) et le Baccalauréat unique (BAC). Le calendrier, les règles et les résultats "
            "changent selon la session : Karamo doit les vérifier sur le site officiel du ministère "
            "avant de donner une date ou un résultat."
        ),
        "keywords": [
            "cee", "bepc", "bac", "baccalauréat unique", "examens nationaux", "école",
            "collège", "lycée", "résultats examens",
        ],
        "source_title": "Ministère de l’Enseignement préuniversitaire et de l’Alphabétisation",
        "source_url": "https://mepua.gov.gn/",
        "priority": 100,
    },
    {
        "slug": "economie-mines-agriculture",
        "category": "ECONOMY",
        "title": "Mines, agriculture et économie",
        "content": (
            "L’économie guinéenne est fortement portée par les activités minières, notamment la "
            "bauxite et l’or. L’agriculture reste essentielle pour l’emploi et les revenus ruraux. "
            "La Banque mondiale souligne que la croissance minière ne se traduit pas automatiquement "
            "par une réduction équivalente de la pauvreté. Les taux de croissance, de pauvreté ou "
            "d’inflation doivent toujours être accompagnés de leur année et vérifiés en ligne."
        ),
        "keywords": [
            "économie", "bauxite", "or", "mines", "simandou", "agriculture", "emploi", "pib",
        ],
        "source_title": "Banque mondiale — Guinea Economic Update 2025",
        "source_url": "https://www.worldbank.org/ext/en/country/guinea",
        "source_published_on": date(2025, 7, 1),
        "priority": 85,
    },
    {
        "slug": "mont-nimba",
        "category": "ENVIRONMENT",
        "title": "Réserve naturelle intégrale du mont Nimba",
        "content": (
            "Le mont Nimba se situe dans une zone transfrontalière entre la Guinée, la Côte "
            "d’Ivoire et le Liberia. La réserve du patrimoine mondial concerne la Guinée et la "
            "Côte d’Ivoire. L’UNESCO décrit un massif culminant à 1 752 mètres, riche en espèces "
            "endémiques et en habitats de montagne. Le site est inscrit au patrimoine mondial "
            "depuis 1981 et demeure un espace de conservation particulièrement sensible."
        ),
        "keywords": [
            "mont nimba", "patrimoine mondial", "unesco", "biodiversité", "crapaud vivipare",
            "chimpanzé", "réserve naturelle",
        ],
        "source_title": "UNESCO — Mount Nimba Strict Nature Reserve",
        "source_url": "https://whc.unesco.org/en/list/155/",
        "priority": 85,
    },
]


def seed_guinea_knowledge():
    """Crée ou actualise les fiches sans écraser leur statut d’activation."""
    from .models import GuineaKnowledgeEntry

    created = 0
    updated = 0
    for item in GUINEA_KNOWLEDGE:
        defaults = {
            **item,
            "verified_on": VERIFIED_ON,
        }
        slug = defaults.pop("slug")
        obj, was_created = GuineaKnowledgeEntry.objects.get_or_create(
            slug=slug, defaults=defaults
        )
        if not was_created:
            for field, value in defaults.items():
                setattr(obj, field, value)
            obj.save()
        created += int(was_created)
        updated += int(not was_created)
    return created, updated
