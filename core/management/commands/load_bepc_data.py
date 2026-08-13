"""
load_bepc_data — Charge des sujets BEPC et Entree en 7eme statiques.
Usage : python manage.py load_bepc_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction

BEPC_SUBJECTS = [
    {
        "title": "BEPC 2023 - Mathematiques",
        "subject": "Mathematiques",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2023
Epreuve de Mathematiques | Duree : 3 heures | Coefficient : 4

EXERCICE 1 (4 points) - CALCUL NUMERIQUE
1. Calculer : A = (3/4 + 1/2) x 8 - (5/6 / 1/3)
2. Simplifier : B = racine(144) + racine(25) - racine(9)
3. Determiner la valeur de : C = 2^3 + 3^2 - 4^1

EXERCICE 2 (6 points) - ALGEBRE
1. Resoudre dans R les equations suivantes :
   a) 2x + 5 = 11
   b) 3(x - 2) = 2x + 1
   c) x/4 - 1/2 = x/3
2. Factoriser les expressions :
   a) 4x^2 - 9
   b) x^2 + 6x + 9
   c) 3x^2 - 12x

EXERCICE 3 (6 points) - GEOMETRIE
Un triangle ABC rectangle en A a AB = 6 cm et AC = 8 cm.
1. Calculer BC.
2. Calculer sin(B), cos(B) et tan(B).
3. Calculer l aire du triangle ABC.
4. M est le milieu de BC. Calculer AM.

EXERCICE 4 (4 points) - STATISTIQUES
Les notes de 10 eleves : 8, 12, 15, 9, 14, 11, 16, 10, 13, 12
1. Calculer la moyenne.
2. Trouver la mediane.
3. Calculer l etendue.""",
    },
    {
        "title": "BEPC 2023 - Francais",
        "subject": "Francais",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2023
Epreuve de Francais | Duree : 3 heures | Coefficient : 4

TEXTE :
Il etait une fois, au bord du fleuve Niger, un vieux pecheur nomme Oumar qui vivait avec sa famille dans un village de pecheurs. Chaque matin avant l aube, il partait sur son embarcation de bois creuse, ramait jusqu au milieu du fleuve et lancait ses filets. Sa patience etait legendaire dans tout le village.

Un jour, ses filets remonterent quelque chose d inhabituel : une tortue geante dont la carapace brillait comme de l or sous le soleil matinal. Plutot que de la garder, Oumar la relача dans les eaux profondes. Le soir meme, une voix mystерieuse s eleva de l eau.

COMPREHENSION DU TEXTE (8 points)
1. Ou et comment vivait Oumar ? (2 pts)
2. Qu a-t-il trouve dans ses filets ce jour-la ? (2 pts)
3. Quelle decision a-t-il prise et pourquoi ? (2 pts)
4. Quelle a ete la recompense de sa bonte ? (2 pts)

VOCABULAIRE (4 points)
1. Trouve dans le texte deux synonymes de vieux.
2. Explique les expressions : avant l aube et legendaire.
3. Forme le contraire de : patience, inhabituel, profond, matinal.

GRAMMAIRE (4 points)
1. Analyse grammaticalement : une tortue geante dont la carapace brillait.
2. Mettez au pluriel : le vieux pecheur partait sur son embarcation.
3. Transformez a la voix passive : Oumar relacha la tortue dans les eaux.

REDACTION (4 points)
En 15 a 20 lignes, racontez une histoire ou un acte de bonte est recompense.""",
    },
    {
        "title": "BEPC 2023 - Physique-Chimie",
        "subject": "Physique-Chimie",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2023
Epreuve de Physique-Chimie | Duree : 2h30 | Coefficient : 3

PARTIE PHYSIQUE (10 points)

EXERCICE 1 - MECANIQUE (5 points)
Un cycliste part du repos et accelere uniformement pour atteindre 36 km/h en 10 secondes.
1. Convertir 36 km/h en m/s.
2. Calculer l acceleration du cycliste.
3. Calculer la distance parcourue pendant ces 10 secondes.

EXERCICE 2 - ELECTRICITE (5 points)
Circuit serie : generateur 12V, R1 = 30 ohms, R2 = 10 ohms.
1. Calculer la resistance equivalente.
2. Calculer l intensite du courant.
3. Calculer la tension aux bornes de R1 et R2.

PARTIE CHIMIE (10 points)

EXERCICE 3 (5 points)
On dispose de : sel (NaCl), sucre, craie (CaCO3), huile, eau.
1. Classer ces substances en melanges homogenes, heterogenes ou corps purs.
2. Comment separer l huile de l eau ?
3. Comment obtenir du sel pur a partir d eau salee ?

EXERCICE 4 - REACTIONS CHIMIQUES (5 points)
Equilibre les equations :
a) H2 + O2 -> H2O
b) Fe + O2 -> Fe2O3
c) CH4 + O2 -> CO2 + H2O""",
    },
    {
        "title": "BEPC 2023 - Histoire-Geographie",
        "subject": "Histoire-Geographie",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2023
Epreuve d Histoire-Geographie | Duree : 2h30 | Coefficient : 2

PARTIE HISTOIRE (10 points)

EXERCICE 1 - LA GUINEE INDEPENDANTE (5 points)
1. En quelle annee la Guinee a-t-elle accede a l independance ?
2. Qui etait le premier president de la Guinee independante ?
3. Qu est-ce que le vote Non du 28 septembre 1958 ?
4. Citez trois realisations importantes de la Premiere Republique.

EXERCICE 2 - L AFRIQUE COLONIALE (5 points)
1. Qu est-ce que la colonisation ?
2. Citez les principales puissances coloniales en Afrique.
3. Quelles ont ete les consequences de la colonisation pour l Afrique ?

PARTIE GEOGRAPHIE (10 points)

EXERCICE 3 - LA GUINEE (5 points)
1. Citez les quatre regions naturelles de la Guinee.
2. Quel est le fleuve le plus important de Guinee ?
3. Quelles sont les principales ressources naturelles de la Guinee ?

EXERCICE 4 - L AFRIQUE (5 points)
1. Combien de pays compte l Afrique ?
2. Citez les cinq plus grandes villes d Afrique.
3. Quels sont les principaux problemes de developpement en Afrique ?""",
    },
    {
        "title": "BEPC 2023 - SVT",
        "subject": "SVT",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2023
Epreuve de Sciences de la Vie et de la Terre | Duree : 2h30 | Coefficient : 2

EXERCICE 1 - BIOLOGIE ANIMALE (6 points)
1. Definir : cellule, tissu, organe, systeme, organisme.
2. Expliquer le role du sang dans l organisme.
3. Decrire le trajet du sang dans le coeur.

EXERCICE 2 - BIOLOGIE VEGETALE (6 points)
1. Ecrire l equation simplifiee de la photosynthese.
2. Quels sont les facteurs necessaires a la photosynthese ?
3. Comparer photosynthese et respiration cellulaire.

EXERCICE 3 - GEOLOGIE (4 points)
1. Qu est-ce qu une roche sedimentaire ? Donnez deux exemples.
2. Comment se forment les roches sedimentaires ?
3. Qu est-ce que le cycle de l eau ?

EXERCICE 4 - ECOLOGIE (4 points)
1. Definir : ecosysteme, chaine alimentaire, biodiversite.
2. Construire une chaine alimentaire : herbe, lion, zebre, bacteries.
3. Citer trois menaces sur la biodiversite en Guinee.""",
    },
    {
        "title": "BEPC 2022 - Mathematiques",
        "subject": "Mathematiques",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2022
Epreuve de Mathematiques | Duree : 3 heures | Coefficient : 4

EXERCICE 1 (4 points) - ARITHMETIQUE
1. Calculer : A = 5/6 + 2/3 - 1/4
2. Calculer : B = (2 + racine(3))(2 - racine(3))
3. Ecrire en notation scientifique : 0,0000456 et 123 000

EXERCICE 2 (6 points) - EQUATIONS ET INEQUATIONS
1. Resoudre dans R :
   a) 5x - 3 = 2x + 9
   b) 2(x + 3) = 3(x - 1)
   c) x^2 - 5x + 6 = 0
2. Resoudre et representer sur un axe :
   a) 3x - 2 > x + 4
   b) -2 inferieur ou egal 2x + 1 < 5

EXERCICE 3 (6 points) - GEOMETRIE DANS L ESPACE
Parallelepipede rectangle : longueur = 12 cm, largeur = 8 cm, hauteur = 5 cm.
1. Calculer son volume.
2. Calculer son aire laterale.
3. Calculer son aire totale.
4. Calculer la longueur de sa diagonale.

EXERCICE 4 (4 points) - FONCTIONS
f(x) = 2x - 1.
1. Calculer f(0), f(1), f(-2), f(3).
2. Dresser un tableau de valeurs pour x de -2 a 3.
3. Tracer la courbe representative de f.""",
    },
    {
        "title": "BEPC 2022 - Francais",
        "subject": "Francais",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2022
Epreuve de Francais | Duree : 3 heures | Coefficient : 4

TEXTE :
La kora est un instrument de musique traditionnel d Afrique de l Ouest. Elle est particulierement associee aux griots, ces musiciens-poetes qui sont les gardiens de la memoire et de l histoire des peuples de la region.

Construite a partir d une calebasse seche recouverte de peau de vache, la kora possede 21 cordes tendues sur un long manche en bois. Son son unique, melangeant les timbres de la harpe et du luth, a seduit des musiciens du monde entier. Mory Kante, artiste guineeen, l a fait connaitre au monde entier avec son titre Yeke Yeke en 1987.

COMPREHENSION (8 points)
1. Qu est-ce que la kora ? Comment est-elle fabriquee ?
2. Qui sont les griots ? Quel est leur role dans la societe ?
3. Quel artiste guineen a fait connaitre la kora au monde ?
4. Relevez dans le texte une comparaison. Expliquez-la.

VOCABULAIRE (4 points)
1. Donnez un synonyme de : associee, unique, seduit, gardiens.
2. Expliquez l expression : gardiens de la memoire.

GRAMMAIRE (4 points)
1. Analysez le groupe nominal : ces musiciens-poetes qui sont les gardiens.
2. Transformez a la forme passive : Mory Kante a fait connaitre la kora.

REDACTION (4 points)
Decrivez un instrument de musique traditionnel de votre region en 15 lignes.""",
    },
    {
        "title": "Entree en 7eme 2023 - Mathematiques",
        "subject": "Mathematiques",
        "level": "6eme",
        "content": """EXAMEN D ENTREE EN 7EME - SESSION 2023
Epreuve de Mathematiques | Duree : 2 heures

EXERCICE 1 - CALCUL (6 points)
1. Calculer :
   a) 345 + 678 - 123
   b) 45 x 23
   c) 840 / 24
   d) 3/4 + 1/2
   e) 5/6 x 3/5
   f) 1/2 / 1/4

2. Trouver le nombre manquant :
   a) 24 x __ = 144
   b) __ / 8 = 15
   c) 3 x __ + 5 = 20

EXERCICE 2 - GEOMETRIE (6 points)
1. Le perimetre d un rectangle est 48 cm. Si sa largeur est 8 cm, quelle est sa longueur ?
2. Calculer l aire d un carre de cote 9 cm.
3. Un triangle a des cotes de 6 cm, 8 cm et 10 cm. Est-il rectangle ? Justifier.

EXERCICE 3 - PROBLEME (8 points)
Un marchand au marche de Madina a Conakry a 240 oranges.
Il vend 1/3 le matin et 1/4 l apres-midi.
1. Combien d oranges vend-il le matin ?
2. Combien vend-il l apres-midi ?
3. Combien lui reste-t-il en fin de journee ?
4. Il vend les oranges a 1 500 GNF l unite. Combien a-t-il gagne en tout ?""",
    },
    {
        "title": "Entree en 7eme 2023 - Francais",
        "subject": "Francais",
        "level": "6eme",
        "content": """EXAMEN D ENTREE EN 7EME - SESSION 2023
Epreuve de Francais | Duree : 2 heures

TEXTE :
Amadou est un eleve de CM2 a l ecole primaire de Ratoma. Chaque matin, il se leve tot pour ne pas etre en retard. Il prepare son sac, mange son petit-dejeuner et part a pied avec ses amis du quartier.

A l ecole, Amadou est tres attentif. Il ecoute bien ses maitres et pose des questions quand il ne comprend pas. C est pourquoi il a toujours de bonnes notes. Le soir, il fait ses devoirs avant de jouer. Sa mere est tres fiere de lui.

COMPREHENSION (6 points)
1. Comment s appelle l eleve ? Dans quelle classe est-il ?
2. Comment se prepare-t-il le matin ?
3. Pourquoi a-t-il de bonnes notes ?
4. Que fait-il le soir avant de jouer ?

VOCABULAIRE (4 points)
1. Trouve dans le texte le contraire de : tard, distrait, mauvaises, impoli.
2. Explique : attentif, respectueux.

GRAMMAIRE (4 points)
1. Souligne les verbes dans la phrase : Amadou prepare son sac et mange son petit-dejeuner.
2. Mets au pluriel : un eleve serieux.
3. Quel est le sujet de ecoute dans la 2eme phrase du 2eme paragraphe ?

REDACTION (6 points)
En 10 lignes, decris ta journee d ecole habituelle.
Commence par : Le matin, je me leve...""",
    },
    {
        "title": "Entree en 7eme 2022 - Mathematiques",
        "subject": "Mathematiques",
        "level": "6eme",
        "content": """EXAMEN D ENTREE EN 7EME - SESSION 2022
Epreuve de Mathematiques | Duree : 2 heures

EXERCICE 1 - CALCUL (6 points)
1. Effectuer les operations suivantes :
   a) 1 245 + 3 678 - 902
   b) 125 x 48
   c) 1 260 / 36
   d) 2/3 + 3/4 - 1/6
   e) 7/8 x 4/7
   f) 5/6 / 5/3

2. Comparer en utilisant < ou > :
   a) 3/4 __ 5/8
   b) 7/12 __ 2/3
   c) 0,75 __ 3/4

EXERCICE 2 - GEOMETRIE (6 points)
1. Tracer un triangle ABC avec AB = 5 cm, BC = 7 cm, AC = 6 cm.
2. Quelle est la nature du triangle si ses angles mesurent 60, 60 et 60 degres ?
3. Calculer le perimetre et l aire d un rectangle de 9 cm sur 6 cm.

EXERCICE 3 - PROBLEME (8 points)
Une ecole de Conakry compte 480 eleves.
Les 2/5 sont des filles.
1. Combien y a-t-il de filles ?
2. Combien y a-t-il de garcons ?
3. Si chaque eleve paie 15 000 GNF de frais de scolarite, quel est le montant total percu ?
4. L ecole depense 80% de cette somme pour les salaires. Combien reste-t-il ?""",
    },
    {
        "title": "BEPC 2021 - Mathematiques",
        "subject": "Mathematiques",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2021
Epreuve de Mathematiques | Duree : 3 heures | Coefficient : 4

EXERCICE 1 (4 points)
1. Calculer sans calculatrice : A = (1/2 + 2/3) x 6/5 et B = 2^4 - 3^2 + 10
2. Ecrire sous forme de fraction irreductible : 0,75 et 1,2
3. Ranger dans l ordre croissant : 2/3, 3/4, 5/8, 7/12

EXERCICE 2 (6 points)
1. Developper et reduire : (x + 3)(x - 2) et (2x - 1)^2
2. Resoudre : 3x - 7 = 2(x + 1) et (x-1)(x+3) = 0
3. Factoriser : x^2 - 4 et x^2 + 4x + 4

EXERCICE 3 (6 points)
Dans un repere orthogonal, on donne les points A(1;3) et B(5;1).
1. Calculer les coordonnees du milieu de AB.
2. Calculer la longueur AB.
3. Ecrire l equation de la droite passant par A et B.

EXERCICE 4 (4 points)
20 eleves ont obtenu les notes suivantes au bac blanc : 
08 09 11 12 14 10 15 08 13 12 11 09 10 14 13 12 11 10 09 15
1. Construire le tableau des effectifs.
2. Calculer la moyenne et la mediane.""",
    },
    {
        "title": "BEPC 2020 - Mathematiques",
        "subject": "Mathematiques",
        "level": "3eme",
        "content": """BREVET D ETUDES DU PREMIER CYCLE (BEPC) - SESSION 2020
Epreuve de Mathematiques | Duree : 3 heures | Coefficient : 4

EXERCICE 1 (4 points)
1. Calculer : A = 3/4 + 5/6 - 1/3 et B = racine(49) + racine(16) - racine(4)
2. Resoudre dans Z : x^2 = 25 et x^2 = -4

EXERCICE 2 (6 points)
1. Resoudre le systeme : 2x + y = 5 et x - y = 1
2. Un robinet remplit un reservoir en 6 heures, un autre en 4 heures.
   En combien de temps remplissent-ils le reservoir ensemble ?

EXERCICE 3 (6 points)
Un prisme droit a base triangulaire. La base est un triangle rectangle
dont les cotes mesurent 3 cm, 4 cm et 5 cm. La hauteur du prisme est 10 cm.
1. Calculer l aire de la base.
2. Calculer le volume du prisme.
3. Calculer l aire laterale.

EXERCICE 4 (4 points)
On lance un de cubique non truque.
1. Quelle est la probabilite d obtenir un nombre pair ?
2. Quelle est la probabilite d obtenir un nombre superieur a 4 ?
3. Quelle est la probabilite d obtenir un nombre premier ?""",
    },
]


class Command(BaseCommand):
    help = "Charge les sujets BEPC et Entree en 7eme"

    def handle(self, *args, **options):
        from learning.models import Document, Subject
        created = updated = 0

        with transaction.atomic():
            for item in BEPC_SUBJECTS:
                subj, _ = Subject.objects.get_or_create(
                    name=item["subject"], defaults={"icon": "📚"}
                )
                obj, is_new = Document.objects.update_or_create(
                    title=item["title"],
                    defaults={
                        "description": f"Sujet officiel {item['title']}.",
                        "doc_type":    "COURS",
                        "subject":     subj,
                        "level":       item["level"],
                        "is_free":     True,
                        "content":     item["content"],
                    }
                )
                status = "cree" if is_new else "maj"
                self.stdout.write(f"  {status} : {item['title']}")
                if is_new: created += 1
                else: updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{created} crees, {updated} mis a jour"
        ))
