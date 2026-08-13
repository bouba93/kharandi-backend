"""
core/content_cleaner.py - Pipeline de nettoyage du contenu scrappe
"""
import re
import logging

logger = logging.getLogger(__name__)

JUNK_PATTERNS = [
    r'exam224\.com[^\n]*', r'Sujets? d[\'\']examens?[^\n]*',
    r'Une panoplie de sujets?[^\n]*', r'Banque de sujets?[^\n]*',
    r'Trouver des? prof[^\n]*', r'Trouver un rep[^\n]*',
    r'\bAccepter\b[^\n]*', r'\bRefuser\b[^\n]*', r'\bFermer\b[^\n]*',
    r'T[ee]l[ee]charger le sujet[^\n]*', r'Voir le corrig[ee][^\n]*',
    r'\bInscription\b[^\n]*', r'\bConnexion\b[^\n]*', r'Se connecter[^\n]*',
    r'[Cc]ookie[^\n]*', r'Ce site n[ee]cessite[^\n]*',
    r'Donn[ee]es personnelles[^\n]*', r'Politique de confidentialit[ee][^\n]*',
    r'J[\'\']accepte[^\n]*', r'RGPD[^\n]*',
    r'Avec amour[^\n]*', r'[Aa] propos[^\n]*',
    r'Conditions d[\'\']utilisation[^\n]*', r'Mentions l[ee]gales[^\n]*',
    r'Tous droits r[ee]serv[ee]s[^\n]*', r'Copyright[^\n]*',
    r'[cC]opyright\s*[©]\s*20\d{2}[^\n]*', r'©\s*20\d{2}[^\n]*',
    r'\bFacebook\b[^\n]*', r'\bInstagram\b[^\n]*', r'\bTwitter\b[^\n]*',
    r'\bYouTube\b[^\n]*', r'\bWhatsApp\b[^\n]*',
    r'S[ee]r[ee]nit[ee] aux examens[^\n]*', r'Vous [eê]tes pr[eê]ts[^\n]*',
    r'Pri[eè]re de nous[^\n]*', r'Contactez[-\s]nous[^\n]*',
    r'donc contenir des erreurs[^\n]*', r'erreurs de frappe[^\n]*',
    r'version transcrite[^\n]*', r'Cette version est[^\n]*',
    r'adresse suivante[^\n]*',
    r'Accueil[^\n]*', r'Retour en haut[^\n]*', r'\bPartager\b[^\n]*',
    r'[EÉ]tude[s]? [àa] l[\'\'][ee]tranger[^\n]*',
    r'<[^>]+>', r'&[a-zA-Z]+;', r'&\#\d+;',
    r'https?://\S+', r'www\.\S+',
]

COMPILED = re.compile('|'.join(JUNK_PATTERNS), re.IGNORECASE | re.MULTILINE)

EXACT_SKIP = {
    'menu', 'accueil', 'retour', 'suivant', 'precedent',
    'partager', 'fermer', 'accepter', 'refuser', 'connexion',
    'inscription', 'rechercher', 'contact', 'facebook', 'instagram',
    'twitter', 'telecharger', 'imprimer', 'copier', 'oui', 'non', 'ok',
}

CONTENT_MARKERS = [
    r'BACCALAUR[EÉ]AT', r'BEPC', r'BREVET', r'EXAMEN',
    r'[EÉ]PREUVE\s+DE', r'Minist[eè]re', r'Exercice\s+\d',
    r'EXERCICE\s+\d', r'Partie\s+[A-Z\d]', r'Probl[eè]me\s*\d',
    r'Session\s+\d{4}', r'Dur[eé]e\s*:', r'Coefficient\s*:',
    r'Calculer', r'D[eé]montrer', r'D[eé]duire',
]
CONTENT_RE = re.compile('|'.join(CONTENT_MARKERS), re.IGNORECASE)


def clean_content(text):
    if not text or len(text) < 50:
        return ''
    text = COMPILED.sub('', text)
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or len(line) < 4:
            continue
        if line.lower() in EXACT_SKIP:
            continue
        if re.match(r'^[^\w\d]*$', line):
            continue
        words = line.split()
        if len(words) == 1 and len(line) > 50:
            continue
        lines.append(line)
    cleaned = []
    empty_count = 0
    for line in lines:
        if not line.strip():
            empty_count += 1
            if empty_count <= 1:
                cleaned.append(line)
        else:
            empty_count = 0
            cleaned.append(line)
    result = '\n'.join(cleaned).strip()
    match = CONTENT_RE.search(result)
    if match:
        start_pos = max(0, result.rfind('\n', 0, match.start() - 1))
        if start_pos > 100:
            result = result[start_pos:].strip()
    return result if len(result) >= 100 else ''


def is_clean_content(text):
    if not text:
        return False
    junk = ['exam224', "sujets d'examens", 'trouver des professeurs',
            'cookie', 'accepter', 'refuser', 'erreurs de frappe', 'version transcrite']
    return not any(j in text.lower() for j in junk)
