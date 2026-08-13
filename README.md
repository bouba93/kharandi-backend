# Kharandi Backend — Final

## 🤖 Karamo AI
L'assistant pédagogique de Kharandi, propulsé par Qwen 2.5-VL via OpenRouter.
- Nom : **Karamo** ("ton compagnon" en Pular/Mandingue)
- Modèle : `qwen/qwen-2.5-vl-7b-instruct`
- Capacités : tutorat socratique, streaming, analyse d'images, QCM, recherche internet et consultation des sujets BAC enregistrés

## Variables d'environnement Render (toutes obligatoires)

| Variable | Valeur |
|---|---|
| `SECRET_KEY` | Clé longue aléatoire |
| `DATABASE_URL` | Internal URL PostgreSQL Render |
| `ALLOWED_HOSTS` | `backfinal-xxxl.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | `https://kharandi.gn,https://www.kharandi.gn` |
| `NIMBA_ACCOUNT_SID` | Ton identifiant Nimba SMS |
| `NIMBA_AUTH_TOKEN` | Ton jeton secret Nimba SMS |
| `NIMBA_SENDER_NAME` | `Kharandi` |
| `LENGOPAY_SITE_ID` | Ton identifiant de site LengoPay |
| `LENGOPAY_LICENSE_KEY` | Ta clé de licence LengoPay |
| `LENGOPAY_WEBHOOK_SECRET` | Secret partagé pour signer les webhooks |
| `LENGOPAY_CURRENCY` | `GNF` |
| `LENGOPAY_COUNTRY` | `GN` |
| `OPENROUTER_API_KEY` | `sk-or-...` |
| `TAVILY_API_KEY` | `tvly-...` |
| `USE_CLOUDINARY` | `False` (ou `True` + 3 vars Cloudinary) |
| `FRONTEND_URL` | `https://kharandi.gn` |
| `ADMIN_PHONE` | Numéro du compte administrateur |
| `ADMIN_PASSWORD` | Mot de passe administrateur fort |
| `DEBUG` | `False` |

## Render — Build Command
```
pip install -r requirements.txt
```

## Render — Start Command
```
bash start.sh
```

## Endpoints Karamo AI

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/ai/status/` | Vérifie la configuration et liste les capacités |
| POST | `/api/v1/ai/ask/` | Chat + recherche internet auto |
| POST | `/api/v1/ai/ask/stream/` | Chat en streaming SSE |
| POST | `/api/v1/ai/ask-image/` | Analyse photo devoir/schéma |
| POST | `/api/v1/ai/generate-qcm/` | Génère 10 QCM |
| POST | `/api/v1/ai/qcm/<id>/submit/` | Corrige les réponses |

Karamo ne révèle pas les solutions d'un QCM avant sa soumission. Une requête IA échouée est remboursée du quota quotidien. Les images sont validées, limitées à 8 Mo et converties en JPEG avant leur envoi à OpenRouter.

### Base de connaissances sur la Guinée

Karamo dispose de fiches sourcées sur la géographie, les régions naturelles et administratives, l'histoire, les langues, les examens nationaux, l'économie et le patrimoine naturel. Elles sont chargées automatiquement par `seed_data` et peuvent aussi être actualisées avec :

```bash
python manage.py seed_guinea_knowledge
```

Les fiches se gèrent dans l'administration Django, rubrique **Connaissances sur la Guinée**. Chaque fiche contient une source, une URL, une date de vérification, des mots-clés, une priorité et un statut actif. Karamo utilise la recherche web pour les dirigeants, calendriers, résultats et statistiques susceptibles de changer.
