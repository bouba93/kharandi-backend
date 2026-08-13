"""
clean_bac_content.py — Nettoie les traces du site exam224.com dans les sujets BAC en base.
Usage : python manage.py clean_bac_content
"""
import re
from django.core.management.base import BaseCommand
from django.db import transaction

JUNK_PATTERNS = [
    r'donc contenir des erreurs[^\n]*',
    r"l'adresse suivante[^\n]*",
    r'Sujets d.examens[^\n]*',
    r'Une panoplie de sujets[^\n]*',
    r'Trouver des professeurs[^\n]*',
    r'Accepter\s*',
    r'Refuser\s*',
    r'Fermer\s*',
    r'Cookie[^\n]*',
    r'RGPD[^\n]*',
    r"j'accepte[^\n]*",
    r'Télécharger le sujet[^\n]*',
    r'Voir le corrigé[^\n]*',
    r'Partager[^\n]*',
    r'Facebook[^\n]*',
    r'Instagram[^\n]*',
    r'Twitter[^\n]*',
    r'Version transcrite[^\n]*',
    r'Cette version est une version[^\n]*',
    r'erreurs de frappe[^\n]*',
    r'Avec amour[^\n]*',
    r'Conditions d.utilisation[^\n]*',
    r'Mentions légales[^\n]*',
    r'Tous droits réservés[^\n]*',
    r'exam224\.com[^\n]*',
    r'banque de sujets[^\n]*',
    r'Trouver un répétiteur[^\n]*',
    r'Trouver son prof[^\n]*',
    r'professeur à domicile[^\n]*',
    r'Sérénité aux examens[^\n]*',
    r'Vous êtes prêts[^\n]*',
    r'Faire une simulation[^\n]*',
    r'Prière de nous[^\n]*',
    r'Contactez-nous[^\n]*',
    r'Étude à l.étranger[^\n]*',
]

JUNK_RE = re.compile('|'.join(JUNK_PATTERNS), re.IGNORECASE)


def clean(text):
    text = JUNK_RE.sub('', text)
    # Supprimer les lignes trop courtes (< 5 chars) qui sont des résidus
    lines = [l for l in text.split('\n') if len(l.strip()) >= 5]
    # Dédupliquer les lignes vides consécutives
    cleaned = []
    prev_empty = False
    for l in lines:
        if not l.strip():
            if not prev_empty:
                cleaned.append(l)
            prev_empty = True
        else:
            cleaned.append(l)
            prev_empty = False
    return '\n'.join(cleaned).strip()


class Command(BaseCommand):
    help = "Nettoie les traces du site scraping dans les sujets BAC en base"

    def handle(self, *args, **options):
        try:
            from learning.models import Document
        except ImportError:
            from content.models import Document

        docs = Document.objects.filter(
            level='Terminale',
            content__gt='',
        )
        total = docs.count()
        cleaned = 0

        with transaction.atomic():
            for doc in docs:
                original = doc.content
                new_content = clean(original)
                if new_content != original:
                    doc.content = new_content
                    doc.save(update_fields=['content'])
                    cleaned += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {total} sujets analysés — {cleaned} nettoyés"
        ))
