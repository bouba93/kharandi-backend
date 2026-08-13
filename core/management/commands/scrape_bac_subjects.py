"""
Scraper BAC Guinée — Version robuste avec debug
"""
import time, re, requests, logging
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

SERIES_CONFIG = {
    'SM': {
        'label': 'BAC SM',
        'subjects': {
            'Mathématiques': 'bac-sm-mathematiques',
            'Physique':      'bac-sm-physique',
            'Chimie':        'bac-sm-se-chimie',
            'Français':      'bac-sm-se-francais',
            'Anglais':       'bac-sm-se-anglais',
            'Philosophie':   'bac-sm-se-philosophie',
            'Économie':      'bac-sm-economie',
        }
    },
    'SS': {
        'label': 'BAC SS',
        'subjects': {
            'SVT':                 'bac-ss-svt',
            'Physique-Chimie':     'bac-ss-physique-chimie',
            'Mathématiques':       'bac-ss-mathematiques',
            'Français':            'bac-ss-francais',
            'Anglais':             'bac-ss-anglais',
            'Philosophie':         'bac-ss-philosophie',
            'Histoire-Géographie': 'bac-ss-histoire-geographie',
        }
    },
    'SE': {
        'label': 'BAC SE',
        'subjects': {
            'Économie':            'bac-se-economie',
            'Mathématiques':       'bac-se-mathematiques',
            'Histoire-Géographie': 'bac-se-histoire-geographie',
            'Français':            'bac-sm-se-francais',
            'Anglais':             'bac-sm-se-anglais',
            'Philosophie':         'bac-sm-se-philosophie',
        }
    },
}

YEARS = list(range(2024, 1999, -1))

# Lignes à supprimer — très ciblées
SKIP_LINES = {
    # Navigation exam224.com
    'exam224', 'sujets d\'examens', 'une panoplie de sujets',
    'trouver des professeurs', 'trouver un répétiteur', 'trouver son prof',
    'professeur à domicile', 'banque de sujets',
    # Boutons / actions
    'accepter', 'refuser', 'fermer', 'télécharger le sujet',
    'voir le corrigé', 'inscription', 'connexion', 'se connecter',
    'chercher un sujet', 'rechercher',
    # Cookies / RGPD
    'cookie', 'ce site nécessite', 'données personnelles',
    'politique de confidentialité', "j'accepte",
    # Footer / mentions
    'avec amour', 'a propos', 'à propos',
    'conditions d\'utilisation', 'mentions légales',
    'tous droits réservés', 'copyright',
    # Réseaux sociaux
    'facebook', 'instagram', 'twitter', 'youtube', 'whatsapp',
    # Pub / promo
    'sérénité aux examens', 'vous êtes prêts',
    'prière de nous', 'contactez-nous', 'contact',
    # Erreurs scraping
    'donc contenir des erreurs', 'erreurs de frappe',
    'cette version est une version transcrite', 'version transcrite',
    'adresse suivante',
    # Navigation générique
    'accueil', 'retour en haut', 'partager',
    'etude à l\'étranger', 'étude à l\'étranger',
    'simulation', 'faire une simulation',
}


class Command(BaseCommand):
    help = "Scrape sujets BAC Guinée depuis exam224.com"

    def add_arguments(self, parser):
        parser.add_argument('--series',  type=str, choices=['SM','SS','SE'])
        parser.add_argument('--year',    type=int)
        parser.add_argument('--subject', type=str)
        parser.add_argument('--delay',   type=float, default=1.5)
        parser.add_argument('--force',   action='store_true',
                            help='Re-scraper même les docs avec contenu')

    def handle(self, *args, **options):
        series_filter  = options.get('series')
        year_filter    = options.get('year')
        subject_filter = options.get('subject')
        delay          = options.get('delay', 1.5)
        force          = options.get('force', False)

        created = skipped = errors = 0

        series_list = ({series_filter: SERIES_CONFIG[series_filter]}
                       if series_filter else SERIES_CONFIG)

        # Session persistante pour éviter de bloquer
        session = requests.Session()
        session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept':          'text/html,application/xhtml+xml,*/*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer':         'https://exam224.com/sujets/browse',
        })
        # Récupérer les cookies d'abord
        try:
            session.get('https://exam224.com/sujets/browse', timeout=10)
        except Exception:
            pass

        for series_key, series_data in series_list.items():
            years = [year_filter] if year_filter else YEARS

            for year in years:
                for subj_name, url_key in series_data['subjects'].items():
                    if subject_filter and subject_filter.lower() not in subj_name.lower():
                        continue

                    title = f"{series_data['label']} {year} — {subj_name}"
                    url   = f"https://exam224.com/sujets/show/{url_key}-{year}"

                    from learning.models import Document
                    existing = Document.objects.filter(title=title).first()

                    # Skip si contenu OK et pas --force
                    if existing and existing.content and len(existing.content) > 200 and not force:
                        self.stdout.write(f"  ⏭  {title}")
                        skipped += 1
                        continue

                    # Scraper
                    content, debug = self._scrape(session, url)

                    if content:
                        self._save(title, content, subj_name, series_key, year, url)
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✅ {title} ({len(content)} chars)"
                        ))
                        created += 1
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠️  {title} — {debug}"
                        ))
                        errors += 1

                    time.sleep(delay)

        self.stdout.write(
            f"\nFini → ✅ {created}  ⏭ {skipped}  ❌ {errors}"
        )

    def _scrape(self, session, url):
        """Retourne (contenu_nettoyé, message_debug)."""
        try:
            resp = session.get(url, timeout=20)
        except Exception as e:
            return "", f"Réseau: {e}"

        if resp.status_code == 404:
            return "", "404"
        if resp.status_code != 200:
            return "", f"HTTP {resp.status_code}"

        html = resp.text

        # Vérification rapide : le contenu est-il dans la page ?
        if 'BACCALAUREAT' not in html.upper() and 'Exercice' not in html:
            # Essayer avec html.parser
            return "", f"Pas de contenu BAC dans la réponse ({len(html)} chars)"

        # Parser avec BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Supprimer nav, footer, scripts
        for tag in soup(['nav', 'footer', 'script', 'style', 'header', 'aside', 'noscript']):
            tag.decompose()

        # Extraire tout le texte
        text = soup.get_text(separator='\n', strip=True)

        # Nettoyer ligne par ligne
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            line_lower = line.lower()
            if any(skip in line_lower for skip in SKIP_LINES):
                continue
            if re.search(r'©\s*20\d{2}', line):
                continue
            lines.append(line)

        result = '\n'.join(lines)

        if len(result) < 100:
            return "", f"Contenu trop court ({len(result)} chars)"

        return result, "OK"

    def _save(self, title, content, subject_name, series, year, url):
        from learning.models import Document, Subject
        with transaction.atomic():
            subject, _ = Subject.objects.get_or_create(
                name=subject_name, defaults={'icon': '📚'}
            )
            Document.objects.update_or_create(
                title=title,
                defaults={
                    'description': (
                        f"Sujet officiel BAC {series} Guinée, session {year}. "
                        f"Épreuve de {subject_name}."
                    ),
                    'doc_type':     'COURS',
                    'subject':      subject,
                    'level':        'Terminale',
                    'is_free':      True,
                    'content':      content,
                    'external_url': url,
                }
            )
