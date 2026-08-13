"""
load_bac_data.py — Sujets BAC Guinée v23 — copiés depuis exam224.com
MEPU-A / SNESCO. Usage : python manage.py load_bac_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction

ICONS = {
    'Mathématiques':'🔢','Physique':'⚡','Chimie':'🧪','Biologie-Géologie':'🔬',
    'Français':'📖','Anglais':'🌍','Philosophie':'💭','Économie':'📈',
    'Géographie':'🗺️','Histoire':'📜','SVT':'🌱',
}

BAC_DATA = [

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2019 — COMPLET 7/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2019,"Mathématiques",4,4,"""BACCALAUREAT SESSION 2019 — BAC SM — Mathématiques — Coeff 4 — 4h
Exercice 1 — Suites (x_n) et (y_n) :
x_0=3, x_(n+1)=2x_n-1 ; y_0=1, y_(n+1)=2y_n+3
1) Démontrer par récurrence x_n=2^(n+1)+1
2a) PGCD(x_8,x_9) et PGCD(x_2002,x_2003). Conclure sur leur primalité.
2b) x_n et x_(n+1) premiers entre eux pour tout n ?
3a) Démontrer 2x_n - y_n = 5 pour tout n. 3b) Exprimer y_n en fonction de n.
3c) Congruences modulo 5. 3d) d_n=PGCD(x_n,y_n). d_n=1 ou 5 ? quand premiers entre eux ?
Exercice 2 — Probabilités :
A) n blanches (n≥2), 5 rouges, 3 vertes. P(deux blanches). p(n)=(n²-n+26)/((n+8)(n+7)).
B) n=4. Joueur mise 30F. Même couleur→40F ; différentes→5F. X=gain. Loi de X. E(X).
Problème — Partie A : g(x)=2e^x+2x-7 sur R. Limites. Variations. g(a)=0 unique, 0,940<a<0,941.
Partie B : f(x)=(2x-5)(1-e^(-x)). Signe. Limites. f'(x)=e^(-x)×g(e^x). Tableau. Tangente. Asymptote D:y=2x-5.
Partie C : Aire entre (C), axes, x=5/2.
Partie D : u_n=C_nB_n/A_nB_n. Nature et limite."""),
("SM",2019,"Physique",3,3,"""BAC SM 2019 — Physique — Coeff 3 — 3h
Théorie : Oscillateur mécanique vs électrique. Transformateur.
1) Rame métro : 160m en 20s, a1 constante. AB=500m, a2=0,2m/s². Vitesse max et durée.
2) Young : λ=0,55µm, D=0,8m, N=10 interfranges. Calculer a. Franges brillante et sombre.
3) Bobine L=10mH, l=30cm, d=5cm. N spires. Energie à I=1,4A."""),
("SM",2019,"Chimie",3,3,"""BAC SM/SE 2019 — Chimie — Coeff 3 — 3h
I (8pts) — Solution tampon pH=9,2 à partir de HCl, NaOH, NH4Cl, NH3. pKA=9,2.
II (6pts) — Estérification CH3COOH+propan-2-ol. Composition équilibre. % acide non estérifié. Autocatalyse.
KMnO4 + acide oxalique : réactif excès et concentration finale.
III (6pts) — Chlorure d'acyle RCOCl : hydrolyse, masse molaire (titrage 19,1cm³ NaOH 1mol/l), obtention RCONH2 et RCONHC2H5."""),
("SM",2019,"Français",2,2,"BAC SM/SE 2019 — Français — Coeff 2 — 2h\nJean Onimus : « Le progrès technique est comme une hache qu'on aurait mis dans les mains d'un psychopathe. »\nPensez-vous que la poésie puisse jouer un rôle libérateur dans une société mécanisée ?"),
("SM",2019,"Anglais",2,2,"BAC SM/SE 2019 — Anglais — Coeff 2 — 2h\nExercices de temps verbaux (Past continuous, Present perfect, Past perfect, 2e Conditionnel, Near future).\nTag questions. Comparatifs. Rédaction sur votre vie depuis 13 ans."),
("SM",2019,"Économie",2,2,"BAC SM 2019 — Économie — Coeff 2 — 2h\nA) L'explosion démographique : réussite ou frein au développement ?\nB) Stratégies contre la dépendance technologique, financière et culturelle."),
("SM",2019,"Philosophie",2,2,"BAC SM/SE 2019 — Philosophie — Coeff 2 — 2h\nEst-il légitime de recourir à la violence pour défendre ses droits ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2020 — 6/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2020,"Mathématiques",4,4,"""BAC SM 2020 — Mathématiques — Coeff 4 — 4h
Exercice 1 (5pts) : a_n=4×10^n-1 ; b_n=2×10^n-1 ; c_n=2×10^n+1. Divisibilité par 3. b3 premier.
b_n×c_n=a_2n. PGCD(b_n,c_n). Equation (E): b3x+c3y=1.
Exercice 2 (5pts) : p(z)=z³-(3+2i)z²+(1+5i)z+2-2i. p(i). p(z)=(z-i)(z²+az+b).
z_0=2. U_n=|z_(n+1)-z_n|=√2/2×|z_n|. Suite géométrique raison √2/2.
Problème (10pts) : g(x)=(x-1)²/(x²+1)+ln(x) sur ]0;+∞[.
f(x)=x·ln(x)-ln(x²+1), f(0)=0. f'(x)=g(x). Unique solution α, 2,22<α<2,23."""),
("SM",2020,"Physique",3,3,"""BAC SM 2020 — Physique — Coeff 3 — 3h
Théorie : Retard établissement/coupure courant dans bobine. Théorème énergie cinétique.
Plan incliné α, V0 en O, piste circulaire rayon r. α=π/4, l=1,6m.
Circuit RLC série : f=100Hz, I_eff=250mA, U_eff=57,8V, avance 60°. Calculer L et R (C=6µF).
Solénoïde N=10⁴, l=0,5m, S=40cm². Courant 0→10A en 5s. B(t). Bobine intérieure 500 spires."""),
("SM",2020,"Chimie",3,3,"""BAC SM/SE 2020 — Chimie — Coeff 3 — 3h
I : Applications de la température sur la vitesse des réactions. Rôle de la trempe.
II : H2O2→H2O+O2. Fe³⁺ catalyseur. V=10cm³, C0=6×10⁻²mol/l. Tableau cinétique. Vitesse moyenne [10;15]min.
III : Acide méthanoïque S0 (80%, d=1,18). C0. V=5cm³→1L. pH(S)=2,4. pKA. Indicateur HIn/In⁻ pKA=5,1."""),
("SM",2020,"Français",2,2,"BAC SM/SE 2020 — Français — Coeff 2 — 2h\nPasteur (1888) : « Deux lois contraires semblent aujourd'hui en lutte, une loi de sang et de mort [...] et une loi de paix, de salut [...] »\nQuelles sont ces deux forces ? Montrez la nécessité d'élargir la loi de paix."),
("SM",2020,"Anglais",2,2,"BAC SM/SE 2020 — Anglais — Coeff 2 — 2h\nTableau de comparatifs/superlatifs. Nombres en lettres. Transformation de phrases. Essai sur l'éducation."),
("SM",2020,"Philosophie",2,2,"BAC SM/SE 2020 — Philosophie — Coeff 2 — 2h\nEinstein : « Le progrès technique est comme une hache qu'on aurait mis dans les mains d'un psychopathe. » En quels sens peut-on affirmer cela ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2018 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2018,"Mathématiques",4,4,"""BAC SM 2018 — Mathématiques — Coeff 4 — 4h
(1+√6)², (1+√6)⁴, (1+√6)⁶. PGCD(847, 342). Suite (1+√6)^n = a_n + b_n√6.
5 ne divise pas a_n+b_n → 5 ne divise pas a_(n+1)+b_(n+1). a_n et b_n premiers entre eux.
z'=z²-4z. Hyperbole H (z imaginaire pur). Centre, sommets, asymptotes. OMMP parallélogramme.
g(x)=ln(1+x)-x. ln(1+a)≤a. f_k(x)=ln(e^x+kx)-x. Variations, limite. f_k(x)≤k/e.
Tangente T_k en O. Position relative (C_p) et (C_m). A(λ)≤k∫₀^λ xe^(-x)dx."""),
("SM",2018,"Physique",3,3,"""BAC SM 2018 — Physique — Coeff 3 — 3h
Théorie : MRUV — espaces pendant intervalles successifs = PA de raison aθ². Fusion nucléaire.
Solénoïde l=1m, R=15cm, N=1000, I=10A. B, L, énergie. Série L=89mH+C=1µF+R=300Ω+GBF f=400Hz, U=10V."""),
("SM",2018,"Anglais",2,2,"BAC SM/SE 2018 — Anglais — Coeff 2 — 2h\nTexte sur attaque de Conakry (22 nov. 1970). Tag questions. Comparatifs. Active→passive. Paragraph sur le bac."),
("SM",2018,"Économie",2,2,"BAC SM 2018 — Économie — Coeff 2 — 2h\nLa dépendance commerciale entre pays développés et pays sous-développés. Mécanismes, causes, conséquences. Solutions."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2017 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2017,"Mathématiques",4,4,"""BAC SM 2017 — Mathématiques — Coeff 4 — 4h
f(x)=e^x/(e^x+1). Primitive. Suite U_n=∫[ln(n);ln(n+1)] f(x)dx. Décroissante positive, limite. S_n limite.
X prend valeurs 1,-1,2 avec proba e^α,e^β,e^γ en PA, E(X)=1. α,β,γ, V(X). Barycentre G.
φ(M)=(1/7)(MA²+2MB²+4MC²). Montrer φ(G)=V(X).
Problème : f(x)=e^(-x)ln(1+e^x) sur R. Deux asymptotes. g(t)=t/(1+t)-ln(1+t). g décroissante.
f'(x) en fonction de g(e^x). Tableau. F(x)=∫₀^x f(t)dt. F(x)=x-ln(1+e^x)-f(x)+2ln2. lim(F(x)-x) en -∞."""),
("SM",2017,"Physique",3,3,"""BAC SM 2017 — Physique — Coeff 3 — 3h
Théorie : Famille radioactive, satellite géostationnaire. Effet photoélectrique.
Bobine l=50cm, S=20cm², N=2000, I=kt (k=5A/s). B, flux, L, f.e.m., énergie à t=1s.
Niveaux H : E_n=-13,6/n² eV. 4 premiers. λ pour n=1→n=3. λ=8,5×10⁻⁸m : énergie cinétique.
Route AB=78km. Vitesses : horizontal=25, montée=15, descente=30 km/h. Δt=24min. Longueurs et durées."""),
("SM",2017,"Chimie",3,3,"""BAC SM/SE 2017 — Chimie — Coeff 3 — 3h
I — Acide faible AH pH=2. Dosage 10ml par NaOH 0,2mol/l. V'=5,5ml. C. pKA. AH dichloroalcanoïque. Formule brute.
II — Acide propénoïque + éthanol. Equation bilan. Caractéristiques. Vitesse V de formation."""),
("SM",2017,"Anglais",2,2,"BAC SM/SE 2017 — Anglais — Coeff 2 — 2h\nsome/any + nom. Nombres cardinaux/ordinaux. Identification de comparatifs/superlatifs."),
("SM",2017,"Philosophie",2,2,"BAC SM/SE 2017 — Philosophie — Coeff 2 — 2h\nEinstein : « Le progrès technique est comme une hache qu'on aurait mis dans les mains d'un psychopathe. »"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2016 — COMPLET 7/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2016,"Mathématiques",4,4,"""BAC SM 2016 — Mathématiques — Coeff 4 — 4h
Proba : n rouges + 2n blanches. P(2 rouges + 2 blanches). P(≥1 blanche). P_n≤1, limite.
A=n-1, B=n²-3n+6. PGCD(A,B)=PGCD(A,4). (n²-3n+6)/(n-1) entier. Couples 2µ+3δ=11 etc.
Barycentres G1, G2. G1G2. Homothétie. Ensemble S : MM1×MM2=0.
h(x)=1+1/x²-2lnx. g(x)=x²(1-lnx)+1+lnx. f(x)=xlnx/(1+x²). g'(x)=xh(x). Tracer (Cf)."""),
("SM",2016,"Physique",3,3,"""BAC SM 2016 — Physique — Coeff 3 — 3h
Rn(222/86)→Pb(206/82) par α et β⁻. Nombre de désintégrations. Masse restante après n périodes.
Young : a=0,200mm, D=1,50m. 5e frange brillante à 34,7mm. Calculer λ.
Voiture 800kg, 75,6km/h, pente 5%, frottements=160N. g=10. Accélération, longueur max, durée montée."""),
("SM",2016,"Chimie",3,3,"""BAC SM/SE 2016 — Chimie — Coeff 3 — 3h
I : HCl (CA=3×10⁻⁴mol/L) + NaOH (CB=7×10⁻⁴mol/L). V=40cm³, pH=3,9. VA et VB. Volume pour pH=7.
II : S2O8²⁻ + I⁻ → I2. Tableau. Vitesse formation I2 à t=40s. Réactif en excès.
III : Ester M=116g/mol → acide éthanoïque + alcool A. Oxydation ménagée → B. Formule brute. Chiralité. Ester."""),
("SM",2016,"Français",2,2,"BAC SM/SE 2016 — Français — Coeff 2 — 2h\nTradition et modernisme se côtoient. Certains les opposent, d'autres les pensent complémentaires. Vos réflexions."),
("SM",2016,"Anglais",2,2,"BAC SM/SE 2016 — Anglais — Coeff 2 — 2h\nTexte à compléter (vocabulaire culture). Nombres en lettres. Correction de phrases. Fautes à corriger."),
("SM",2016,"Économie",2,2,"BAC SM 2016 — Économie — Coeff 2 — 2h\nMontrez et expliquez les relations entre les secteurs agricole et industriel."),
("SM",2016,"Philosophie",2,2,"BAC SM/SE 2016 — Philosophie — Coeff 2 — 2h\nPaul Ricœur : « La démocratie n'est pas un régime sans conflits, mais un régime dans lequel les conflits sont ouverts et négociables. » Partagez-vous ce point de vue ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2015 — 7/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2015,"Mathématiques",4,4,"""BAC SM 2015 — Mathématiques — Coeff 4 — 4h
Σk(n-k)=(n-1)n(n+1)/6. 10^(9n+2)+10^(6n+1)+1 divisible par 111. Décomposer 469. x³-y³=469 dans N².
Rotation z'=ze^(iθ). z²/2+4z√3+32=0. Triangle OAB nature. C → D par rotation π/3. G barycentre.
Problème : g(x)=(2x+1)/x²+lnx. f(x)=(1/x-lnx)e^(-x). Tangente. Primitive h(x)=e^(-x)lnx. Aire A(Υ) pour Υ>3."""),
("SM",2015,"Physique",3,3,"""BAC SM 2015 — Physique — Coeff 3 — 3h
Théorie : Troisième loi de Kepler. Loi de Laplace.
Mobile m=20kg, V0=4m/s, α=20°, frottement f=40N. Distance avant arrêt. Vitesse en descente. g=9,8 ; sin20°=0,34.
Solénoïde l=40cm, 1250sp/m, R=2cm, I=5A. B. Flux. L. µ0=4π×10⁻⁷.
P radioactif β⁻. Equation désintégration (noyau fils S). T=14,3j. λ radioactive."""),
("SM",2015,"Chimie",3,3,"BAC SM/SE 2015 — Chimie — Coeff 3 — 3h\n(URL : bac-sm-se-chimie-1993 sur exam224.com — sujet commun 2015/SE)\nMélange acide faible + base. Cinétique. Synthèse organique."),
("SM",2015,"Français",2,2,"BAC SM/SE 2015 — Français — Coeff 2 — 2h\n« Si la civilisation est un fait universel, il y a tout de même des civilisations. »\nExpliquez cette pensée d'un écrivain contemporain."),
("SM",2015,"Anglais",2,2,"BAC SM/SE 2015 — Anglais — Coeff 2 — 2h\nTexte sur accident de route en Guinée. Tag questions. Essai sur les accidents de la route."),
("SM",2015,"Économie",2,2,"BAC SM 2015 — Économie — Coeff 2 — 2h\nMalgré les efforts, le chômage devient un problème brûlant dans les PSD.\nCauses et conséquences. Solutions pour lutter contre le chômage."),
("SM",2015,"Philosophie",2,2,"BAC SM/SE 2015 — Philosophie — Coeff 2 — 2h\n« L'individu n'a point de droit, il n'a que des devoirs. » Dissertez."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2014 — COMPLET 7/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2014,"Mathématiques",4,4,"""BAC SM 2014 — Mathématiques — Coeff 4 — 4h
a=111, b=114, c=13054 en base n. Sachant c=ab, trouver n. PGCD et ax+by=1 dans Z².
X prend valeurs 1,-1,2 avec e^a,e^b,e^c (PA), E(X)=1. V(X). Barycentre G. φ(M)=(1/7)(MA²+2MB²+4MC²). φ(G)=V(X). Γ des M tels φ(M)=3.
Problème A : g(x)=(1-x)e^(1-x)-1. Limites. g'(x)=(x-2)e^(1-x). Unique solution α. Signe de g.
Partie B : f(x)=xe^(1-x)-x+2. f primitive de g. Asymptote oblique D:y=-x+2."""),
("SM",2014,"Physique",3,3,"""BAC SM 2014 — Physique — Coeff 3 — 3h
Théorie : Loi attraction universelle. Relation λ ↔ énergie de transition (eV).
Archer, D=50m, h=0,5m, V0=50m/s. Equation trajectoire. Angle d'inclinaison. g=9,8.
Particule énergie=938MeV. Vitesse quand énergie totale=double énergie repos. C=3×10⁸m/s.
Spire R=10cm, d=0,1mm, ρ=1,6×10⁻⁸Ω.m dans B=0,2T, f=50Hz. I_induit. I_efficace."""),
("SM",2014,"Chimie",3,3,"""BAC SM/SE 2014 — Chimie — Coeff 3 — 3h
I — pH=4,12. Mélange HCOOH + NaOH (2×10⁻²mol/l). Volumes. pKA=3,8. Concentrations espèces.
Volume formiate 0,2N à ajouter à HCOOH 0,1N pour pH=3,6.
II — 3mol HCOOH + 2mol éthanol. Dosages à 45min et 1h40min. Composition et vitesse moyenne.
III — 10cm³ éthylamine + V cm³ HCl 2×10⁻¹mol/l. pH=10. Trouver V. V pour pH=pKA=10,8.
IV — Chlorure d'acétyle + alcool A (M=74g/mol). Formule brute. Isomères. Oxydation ménagée → B (DNPH ✓, Fehling ✗). Masse ester."""),
("SM",2014,"Français",2,2,"BAC SM/SE 2014 — Français — Coeff 2 — 2h\nMontesquieu : « Aujourd'hui nous recevons trois éducations différentes ou contraires : celle de pères, celle de l'école et celle du monde. Ce qu'on vous dit dans la dernière renverse toutes les idées premières. »\nEn quoi cette pensée est-elle actuelle ? Comment concilier ces trois éducations ?"),
("SM",2014,"Anglais",2,2,"BAC SM/SE 2014 — Anglais — Coeff 2 — 2h\nTexte : accident de route (homme meurt, fils blessé, médecin crie « mon fils »). Compréhension (6pts).\nGrammaire (Passive, Simple Past, Conditionnels, Comparatifs) (7pts). Paragraph (4pts)."),
("SM",2014,"Économie",2,2,"BAC SM 2014 — Économie — Coeff 2 — 2h\nLes transports : facteur de développement. Faiblesses, causes, conséquences. Solutions."),
("SM",2014,"Philosophie",2,2,"BAC SM/SE 2014 — Philosophie — Coeff 2 — 2h\nJean Rostand : « La science fait de nous des dieux avant que nous méritions d'être des hommes. » Expliquez et commentez."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2013 — 6/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2013,"Mathématiques",4,4,"""BAC SM 2013 — Mathématiques — Coeff 4 — 4h
(E): 8x+5y=1 dans Z. Solution particulière. Résolution. N entier avec couple (a,b). Montrer (a,-b) solution. Reste de N÷40.
Triangle ABC rect. en A, AB=2a, AC=a. Barycentre G de (A,1),(B,-1),(C,1).
Ensemble (C) des M : ||MA-MB+MC||=||MA+MB-2MC||. H : AH=½AB-AC. H barycentre de (A,3),(B,1),(C,-2).
Problème : f(x)=x²/2+x-2xlnx sur ]0;+∞[. Variations. Asymptote oblique. Tangente. Intégration par parties."""),
("SM",2013,"Physique",3,3,"""BAC SM 2013 — Physique — Coeff 3 — 3h
U-238 → Pb-226 par α et β. Nombre de particules α et β émises.
Projectile V0=30m/s, angle 60°. Equation trajectoire. Flèche. Angle pour flèche maximale. Point E sur plan incliné 30°.
RLC série : R=50Ω, L=45mH (r=10Ω), C=10µF, U_eff=6V, f=100Hz. I_eff. Tensions aux bornes.
Photoélectricité : cathode potassium λ0=0,55µm, λ=0,50µm. Vitesse max des électrons émis."""),
("SM",2013,"Chimie",3,3,"""BAC SM/SE 2013 — Chimie — Coeff 3 — 3h
I — Solution tampon HCOOH/HCOO⁻ (KA=1,6×10⁻⁴) : 20cm³+10cm³ NaOH 0,1mol/l.
pH de la solution tampon. Volume HCl 0,1mol/l à ajouter pour pH=3,5.
II — S2O8²⁻ + I⁻ → I2. Vitesse moyenne disparition KMnO4. Vitesse formation CO2.
III — Alcène A + eau → alcool B → ester C (M=116g/mol). Formule brute de B. Formules A, B, C. Chiralité. Enantiomères. Isomères."""),
("SM",2013,"Français",2,2,"BAC SM/SE 2013 — Français — Coeff 2 — 2h\nQuelle que soit la branche professionnelle dans laquelle elle s'exerce, la formation se doit de préparer les jeunes à l'adaptation. Expliquer cette assertion."),
("SM",2013,"Anglais",2,2,"BAC SM/SE 2013 — Anglais — Coeff 2 — 2h\n1. Décrire un itinéraire depuis la maison d'Ali jusqu'à l'école (à partir d'une carte). (5pts)\n2. Exercices de grammaire."),
("SM",2013,"Économie",2,2,"BAC SM 2013 — Économie — Coeff 2 — 2h\nMalgré les efforts, le chômage devient un problème brûlant dans les PSD.\nCauses et conséquences de ce fléau. Solutions pour lutter contre le chômage."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2012 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SM",2012,"Mathématiques",4,4,"""BAC SM 2012 — Mathématiques — Coeff 4 — 4h
PGCD(4⁵-1, 4⁶-1). Suite U_0=1, U_1=5, U_(n+2)=5U_(n+1)-4U_n.
U_(n+1)=4U_n+1. U_n entier naturel. PGCD(U_n,U_(n+1)).
V_n=U_n+1/3 : géométrique raison 4. V_n puis U_n. PGCD(4^(n+1)-1, 4^n-1).
s application Z_1=(-1+i)Z+1+4i. Nature et éléments caractéristiques. Transformées de x=0 et y=x-1.
Problème A) g(x)=1+x-xlnx, g(0)=1. Continuité et dérivabilité en 0. Variations. g(x)=0, 3,5<β<3,6.
B) f(x)=lnx/(1+x)²+2. f'(x)=g(x)/(x(1+x)²). Tableau. Point A. Construire (Cf)."""),
("SM",2012,"Physique",3,3,"""BAC SM 2012 — Physique — Coeff 3 — 3h
Théorie : Loi de Laplace. Notion d'apesanteur. Loi de Lenz.
Bobine L=0,636H, U=100V, I=0,50A en continu. En alternatif U=100V, f=50Hz.
Impédance et I_eff. i=Im·sin(ωt+φ). Chaleur dégagée en 5min. C pour facteur de puissance=1.
Automobiliste 126km/h, obstacle D=100m. Freine : 90km/h en t=1,6s. Décélération. Distance d'arrêt. Avec temps de réaction 1s."""),
("SM",2012,"Chimie",3,3,"""BAC SM/SE 2012 — Chimie — Coeff 3 — 3h
I — 20cm³ HCl 10⁻²mol/l + V cm³ NaOH 1,5×10⁻²mol/l. pH=2,5. Concentrations en fonction de V. Trouver V. Volume NaOH pour équivalence.
II — S2O8²⁻ + I⁻ : [I2] augmente de 6×10⁻³mol/l en 130s. Vitesses formation I2 et ions sulfate.
III — Alcool A (M=74g/mol). Oxydation ménagée → B (DNPH ✓, AgNO3 ✗). Formule brute. Isomères. B, oxydation énergique → acide. Décarboxylation → alcane D. Mécanisme D+Cl2."""),
("SM",2012,"Anglais",2,2,"BAC SM/SE 2012 — Anglais — Coeff 2 — 2h\nTag questions (6). Choisir mots de la liste pour 8 phrases. Noun clauses (reporter les paroles). Lettre jumblées. Conditionnels. have/has + since/for. Transformer paragraphe Elizabeth (présent→passé)."),
("SM",2012,"Économie",2,2,"BAC SM 2012 — Économie — Coeff 2 — 2h\nMalgré l'importance de l'agriculture dans le développement socio-économique, son résultat est loin d'être brillant dans les PSD.\nCauses et conséquences de cette médiocrité. Solutions pour relancer cette activité."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2021 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2021,"Philosophie",3,3,"BAC SS 2021 — Philosophie — Coeff 3 — 3h\nLes sciences de l'homme doivent-elles s'inspirer des méthodes utilisées dans les sciences de la nature ?"),
("SS",2021,"Histoire",2,2,"""BAC SS 2021 — Histoire — Coeff 2 — 2h
A l'issue de la deuxième guerre mondiale, les hommes épris de paix prétendent pour la deuxième fois dans l'histoire de l'humanité, matérialiser le très vieux rêve de paix universelle et permanente. Cet outil, tout en se montrant incontestablement plus efficace que le premier, révèle de nouvelles insuffisances.
Près de quatre décennies, l'instrument africain créé et considéré comme « lueur d'espoir des africains », semble être plongé dans les ténèbres qui risquent de retarder son action. Expliquez."""),
("SS",2021,"Géographie",2,2,"""BAC SS 2021 — Géographie — Coeff 2 — 2h
Avec moins de 3% des actifs, l'agriculture américaine nourrit sa population et alimente un fort courant commercial intérieur et extérieur.
L'Inde aussi a connu la famine mais l'a vaincue.
Le gouvernement guinéen a annoncé un programme de dynamisation des activités agricoles pour réaliser l'autosuffisance alimentaire dans un bref délai.
En vous appuyant sur vos connaissances de l'agriculture américaine et de la Révolution verte indienne, lequel des deux modèles proposeriez-vous à votre gouvernement pour réussir ce pari ?"""),
("SS",2021,"Mathématiques",2,2,"""BAC SS 2021 — Mathématiques — Coeff 2 — 2h
Exercice : Urne avec 3 boules noires et 4 blanches. Tirage simultané de 2.
1) P(deux blanches) ? 2) P(deux noires) ? 3) P(deux couleurs différentes) ?
Problème : f(x)=e^(2x)-e^x-2, courbe (C), 4cm=1unité en abscisse, 1cm=1 unité en ordonnée.
Ensemble de définition. Limite en -∞. Asymptote D : y=-2. Montrer f(x)=(e^x(e^x-1))-2.
Dérivée f'. f'(x)=e^x(e^x-1). Sens de variation. Tableau. f(x)=(e^x-2)(e^x+1). Intersection avec axe x.
Table de valeurs pour x=-1,0,1,2. Construire (C). e=2,7."""),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2020 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2020,"Français",4,4,"""BAC SS 2020 — Français — Coeff 4 — 4h
Simone Veil :
« Beaucoup de bon esprit considèrent que le fléau du monde moderne, ce n'est pas de la vitesse, ni le bruit, ni la publicité, ni même la pollution, mais une résistible marche vers l'uniformité à travers le monde. Aujourd'hui l'uniformité s'est abattue partout. »
En prenant des exemples dans différents domaines, discutez la position de Simone Veil concernant la place grandissante de cette uniformité et analysez les conséquences possibles de ce phénomène."""),
("SS",2020,"Philosophie",3,3,"BAC SS 2020 — Philosophie — Coeff 3 — 3h\nL'art naquit et se développa sous les auspices des rois et des empereurs.\nDe ce qui inspire l'histoire des empires médiévaux, démontrez l'existence de l'art africain."),
("SS",2020,"Histoire",2,2,"""BAC SS 2020 — Histoire — Coeff 2 — 2h
Les jeunes états d'Afrique, pour s'affirmer à la face du monde, ont créé une organisation continentale :
1. Cette organisation porte aujourd'hui un autre nom, lequel ? Donnez sa date et son lieu de naissance.
2. Citez ses objectifs et montrez s'ils ont été atteints.
3. Qui en est l'actuel président ? La méditerranée constitue un gigantesque cimetière pour des milliers de jeunes africains. Dégagez les causes de cette situation dramatique. Montrez son impact dans l'évolution socioéconomique africaine et proposez des solutions."""),
("SS",2020,"Géographie",2,2,"""BAC SS 2020 — Géographie — Coeff 2 — 2h
I. Les pays africains possèdent d'importants gisements de bauxite, fer, cuivre, uranium, cobalt, argent, or, diamant… et d'importants cours d'eau.
1) Donnez les raisons de cette situation que vit l'Afrique.
2) Que faut-il pour un développement durable du continent africain ?
II. Le Brésil est un grand pays de contrastes physiques, sociaux et économiques.
1. Expliquez ses contrastes.
2. Démontrez que, malgré sa puissance industrielle, le Brésil est considéré comme un pays sous-développé."""),
("SS",2020,"Économie",2,2,"""BAC SS 2020 — Économie — Coeff 2 — 2h
La faiblesse de l'épargne intérieure est l'une des raisons fondamentales de la dépendance financière des pays sous-développés.
1) Dégagez les causes et conséquences de ce phénomène.
2) Proposez des approches de solutions pour les pays sous-développés."""),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2019 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2019,"Français",4,4,"""BAC SS 2019 — Français — Coeff 4 — 4h
Guy de Maupassant :
« Le romancier transforme la vérité déplaisante pour en tirer une intrigue séduisante. Donne de l'armature à la vraisemblance, falsifie les évènements pour plaire au lecteur. La trame de son roman est une savante combinaison qui conduit au dénouement. »
A travers la revue d'au moins un roman du programme, démontrez la véracité de ce constat."""),
("SS",2019,"Philosophie",3,3,"BAC SS 2019 — Philosophie — Coeff 3 — 3h\nEst-il légitime de recourir à la violence pour défendre ses droits ?"),
("SS",2019,"Géographie",2,2,"""BAC SS 2019 — Géographie — Coeff 2 — 2h
Tableau de population par sexe et âge (total 11.824.562 habitants). Tranches de 0-4 à 79+.
1) Pyramide des âges. 2) Forme et caractéristiques.
3) Proportion jeunes (0-19), adultes (20-59), vieux (60+). 4) Diagramme circulaire.
545.550 naissances vivantes et 56.125 décès. 5) Taux d'accroissement naturel."""),
("SS",2019,"Économie",2,2,"BAC SS 2019 — Économie — Coeff 2 — 2h\nAprès avoir expliqué les causes et les effets de l'endettement des pays en développement, montrez ce qu'il faut pour que ces pays sortent de cet état de dépendance."),
("SS",2019,"Mathématiques",2,2,"""BAC SS 2019 — Mathématiques — Coeff 2 — 2h
Exercice (10pts) : Ferme d'élevage. Production hebdomadaire de lait par tranches [65;75[, [75;80[, [80;85[, [85;90[, [90;95[, [95;100[, [100;110[, [110;120[. Effectifs : 40,30,45,58,33,24,20,14.
1) Diagramme des effectifs cumulés croissants.
2) Production laitière médiane. Vérification graphique.
3) Premiers et troisièmes quartiles. Vérification graphique.
4) Calculer la moyenne.
Problème (10pts) : f(x)=ln((x+3)/(x-1)).
1) Ensemble de définition. 2) Limites aux bornes. 3) Dérivée. Tableau de variation.
4) Montrer que A(-1;0) est un centre de symétrie. 5) Tracer la courbe."""),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2018 — 1/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2018,"Économie",2,2,"BAC SS 2018 — Économie — Coeff 2 — 2h\nL'agriculture est la pierre angulaire de l'économie des pays. Malgré les efforts, les résultats restent insuffisants dans les pays sous-développés. Dégagez les causes et les conséquences. Proposez des solutions."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2017 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2017,"Français",4,4,"BAC SS 2017 — Français — Coeff 4 — 4h\nJ.M.G. Le Clézio : « L'artiste est celui qui nous montre du doigt une parcelle du monde. »\nEn quoi les artistes vous ont-ils fait découvrir des aspects du monde et de la vie ? Trouvez des illustrations précises dans la littérature ou dans d'autres formes d'art."),
("SS",2017,"Philosophie",3,3,"BAC SS 2017 — Philosophie — Coeff 3 — 3h\nVictor Hugo (« William Shakespeare », 1864) : « Ah ! Esprits, soyez utiles, servez à quelque chose. Ne faites pas les dégoutés, quand il s'agit d'être bons et efficaces. L'art pour l'art peut être bon, mais l'art pour le progrès est plus beau encore »."),
("SS",2017,"Histoire",2,2,"""BAC SS 2017 — Histoire — Coeff 2 — 2h
Les jeunes états d'Afrique, pour s'affirmer à la face du monde, ont créé une organisation continentale :
1. Cette organisation porte aujourd'hui un autre nom, lequel ? Donnez sa date et son lieu de naissance.
2. Citez ses objectifs et montrez s'ils ont été atteints.
3. Qui en est l'actuel président ? De nos jours, la méditerranée constitue un gigantesque cimetière pour des milliers de jeunes africains. Dégagez les causes de cette situation dramatique, montrez son impact dans l'évolution socioéconomique du continent africain et proposez des solutions."""),
("SS",2017,"Géographie",2,2,"BAC SS 2017 — Géographie — Coeff 2 — 2h\nLes voies de communication constituent pour l'économie d'un pays ce que sont les veines pour l'organisme d'être vivant."),
("SS",2017,"Économie",2,2,"BAC SS 2017 — Économie — Coeff 2 — 2h\nLe déséquilibre économique survenant quand la demande de travail est supérieure à l'offre dans les pays sous-développés aboutit à une inactivité des personnes.\nNommez cette situation. Causes et conséquences. Moyens de lutte."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2016 — 3/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2016,"Français",4,4,"BAC SS 2016 — Français — Coeff 4 — 4h\nLes romans des auteurs francophones africains des années 90 se sont démarqués fortement de ceux qui les ont précédés. Faites ressortir en quoi les romans de ces périodes diffèrent et montrez que malgré cette différence, ils ne poursuivent qu'un seul objectif."),
("SS",2016,"Philosophie",3,3,"BAC SS 2016 — Philosophie — Coeff 3 — 3h\nJP Sartre : « Ce qu'il y a de commun entre l'art et le moral, c'est que dans les deux cas nous avons création et invention ». À l'aide d'exemples précis, expliquez, commentez et justifiez cette pensée."),
("SS",2016,"Histoire",2,2,"BAC SS 2016 — Histoire — Coeff 2 — 2h\nLa vieille ville de Jérusalem est construite sur les vestiges de 3000 ans de peuplement continu. Elle est dite trois fois Sainte car au cœur du patrimoine des trois monothéismes. Dans cette localité s'affrontent deux communautés religieuses.\n1. Expliquez et commentez cet extrait de texte.\n2. Que savez-vous de ce conflit ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2015 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2015,"Français",4,4,"BAC SS 2015 — Français — Coeff 4 — 4h\nCésaire (La Tragédie du roi Christophe) : « Les nations indépendantes doivent garder à la fois leur autonomie et s'adapter aux exigences du monde moderne. » Expliquer et commenter."),
("SS",2015,"Philosophie",3,3,"BAC SS 2015 — Philosophie — Coeff 3 — 3h\nBoileau : « Il n'y a pas de monstre odieux qui par l'art imité ne puisse plaire aux yeux. » Partagez-vous cet avis ?"),
("SS",2015,"Anglais",3,3,"""BAC SS 2015 — Anglais — Coeff 3 — 3h
I. Texte sur l'hydroélectricité en Guinée. Compléter avec les mots : Largest/much/many/electricity/work/appliances/several/problems. (8pts)
Questions de compréhension.
II. Exercices de grammaire. Essai."""),
("SS",2015,"Économie",2,2,"BAC SS 2015 — Économie — Coeff 2 — 2h\n« Pour un vrai développement, l'aide extérieure doit être secondaire. »\na) Expliquez et dégagez les conséquences d'une économie dépendante.\nb) Comparez coopération sud-sud et nord-sud.\nc) Laquelle peut rapidement développer un pays sous-développé ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2014 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2014,"Français",4,4,"BAC SS 2014 — Français — Coeff 4 — 4h\nLa liberté est-elle l'affranchissement de toute autorité ?\nEn vous inspirant des œuvres du programme et de vos expériences, montrez que la liberté vient de la connaissance et du respect de la loi."),
("SS",2014,"Philosophie",3,3,"BAC SS 2014 — Philosophie — Coeff 3 — 3h\nNicolas Boileau (Art poétique) : « Il n'y a point de serpent ou de monstre odieux qui par l'art imité ne puisse plaire aux yeux. » Que vous inspire cette affirmation ?"),
("SS",2014,"Anglais",3,3,"BAC SS 2014 — Anglais — Coeff 3 — 3h\nTexte : La hyène et le singe. Compléter avec les mots (hungry/replied/branches/ago/story/upset/back/doing/she/goat/down). Compréhension. Grammaire. Essai."),
("SS",2014,"Géographie",2,2,"BAC SS 2014 — Géographie — Coeff 2 — 2h\n1) La mécanisation n'est pas encore effective en Guinée, le Japon est au stade de l'automation. Parallèle entre les deux pays (modes, moyens, méthodes de production). Causes du retard et du progrès.\n2) Décrivez la structure géologique de la Guinée."),
("SS",2014,"Économie",2,2,"BAC SS 2014 — Économie — Coeff 2 — 2h\nIl apparait clairement que la dette extérieure des pays pauvres n'a pas été le moyen le plus sûr pour accélérer leur croissance économique. Expliquez et montrez comment passer de l'état d'endettement chronique à celui du progrès économique."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2013 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2013,"Français",4,4,"BAC SS 2013 — Français — Coeff 4 — 4h\nLa valeur d'une œuvre littéraire tient-elle à ce qu'elle traite des sujets utiles en relation avec les préoccupations du moment ?\nVous fonderez votre réflexion sur des exemples précis tirés de romans, pièces de théâtre lus ou étudiés."),
("SS",2013,"Philosophie",3,3,"BAC SS 2013 — Philosophie — Coeff 3 — 3h\nRousseau : « Le plus fort n'est jamais assez fort pour être toujours le maître, s'il ne transforme sa force en droit, et l'obéissance en devoir. »"),
("SS",2013,"Anglais",3,3,"BAC SS 2013 — Anglais — Coeff 3 — 3h\nDialogue : La ville et le village (Fodé et Maria). Comparaisons (more interesting, more dangerous, friendlier, busier, slower, healthier, faster, more expensive). Compréhension. Grammaire. Essai."),
("SS",2013,"Économie",2,2,"BAC SS 2013 — Économie — Coeff 2 — 2h\n« L'assistance apportée par les pays développés aux pays sous-développés doit être secondaire. »\nQuels sont les voies et moyens que nous devons adopter pour amorcer un vrai développement ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2012 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2012,"Français",4,4,"BAC SS 2012 — Français — Coeff 4 — 4h\n« La littérature et le cinéma sont deux moyens d'expression. Lequel des deux selon vous paraît le plus apte à faire réfléchir les hommes sur les grands problèmes qui se posent à la société de nos jours ? Appuyez votre argumentation d'exemples précis. »"),
("SS",2012,"Philosophie",3,3,"BAC SS 2012 — Philosophie — Coeff 3 — 3h\nPascal : « La justice sans la force est impuissante, la force sans la justice est tyrannique. »"),
("SS",2012,"Anglais",3,3,"BAC SS 2012 — Anglais — Coeff 3 — 3h\nTexte sur Running Wolf, amérindien de 12 ans et la cérémonie d'initiation. Compléter avec (Important/wolf/vision/tell/boys/arrived/ceremony/participate/community/since). Compréhension. Grammaire. Essai."),
("SS",2012,"Géographie",2,2,"BAC SS 2012 — Géographie — Coeff 2 — 2h\nKizerbro : « Le prix des matières monte par escalier, celui des produits manufacturés grimpe par ascenseur. »\n1) Montrez que le Nigeria aurait pu être un NPI. 2) Que la Guinée ne devrait pas manquer d'eau et d'électricité. 3) Le problème du développement n'est pas seulement un problème de richesses naturelles."),
("SS",2012,"Économie",2,2,"BAC SS 2012 — Économie — Coeff 2 — 2h\nLa République de Guinée, considérée comme un pays à scandale géologique et agricole, fait partie des pays les moins avancés.\nQuelles sont selon vous les voies et moyens pour qu'elle devienne un pays émergent ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2011 — 3/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2011,"Français",4,4,"BAC SS 2011 — Français — Coeff 4 — 4h\n« La littérature africaine des années 60 est qualifiée de littérature de contestation. »\nEn vous appuyant sur des exemples précis, montrez la véracité de cette affirmation."),
("SS",2011,"Philosophie",3,3,"BAC SS 2011 — Philosophie — Coeff 3 — 3h\n« Sans l'État, ce serait la guerre de tous contre tous. » Expliquez cette affirmation."),
("SS",2011,"Économie",2,2,"BAC SS 2011 — Économie — Coeff 2 — 2h\n« La pauvreté n'est pas une fatalité. » Expliquez cette affirmation et montrez comment les pays sous-développés peuvent en sortir."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2010 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2010,"Français",4,4,"BAC SS 2010 — Français — Coeff 4 — 4h\n« La littérature africaine des années 60 est qualifiée de contestation, de bouleversement à travers laquelle se construit aujourd'hui la nouvelle Afrique : l'Afrique des démocraties. »\nEn vous appuyant sur des œuvres lues et étudiées, développez cette thèse."),
("SS",2010,"Philosophie",3,3,"BAC SS 2010 — Philosophie — Coeff 3 — 3h\nBossuet : « Sans État, ce serait la guerre de tous contre tous. Livrés à eux-mêmes, les hommes s'entre-déchireraient au gré de leurs passions désordonnées. » Expliquez cette affirmation."),
("SS",2010,"Géographie",2,2,"BAC SS 2010 — Géographie — Coeff 2 — 2h\nSur le fond d'une carte de la République de Guinée, tracez le profil du fleuve Konkouré et de ses affluents. Localisez les barrages hydroélectriques en activité et en projet. Préfectures couvertes. Importance du réseau Konkouré. Grands traits du climat et de végétation."),
("SS",2010,"Économie",2,2,"BAC SS 2010 — Économie — Coeff 2 — 2h\nRôle et place des activités du secteur primaire dans le développement des pays sous-développés."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2009 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2009,"Français",4,4,"BAC SS 2009 — Français — Coeff 4 — 4h\nI. Alain : « S'il est vrai que la beauté d'un objet n'est pas manifeste pour chaque spectateur, il faut affirmer que rien n'est vraiment beau et que tout peut être beau pour qui sait voir et relier les choses entre elles. » Commentez ce point de vue.\nII. « Aucun livre ne sort directement des battements d'un cœur. Une littérature existe dans une société donnée, elle en reçoit l'empreinte et en retour lui imprime une direction. » Expliquer et commenter."),
("SS",2009,"Philosophie",3,3,"BAC SS 2009 — Philosophie — Coeff 3 — 3h\nBaruch Spinoza : « La contingence ne se trouve pas dans la nature. Mais elle se trouve dans l'ignorance des causes. » Expliquez cette affirmation."),
("SS",2009,"Anglais",3,3,"BAC SS 2009 — Anglais — Coeff 3 — 3h\nI. Écrire une question logique pour chaque réponse (6). II. Ordonner des phrases en deux paragraphes : « working women — a bad idea » et « working — a good idea ». III. Essai."),
("SS",2009,"Géographie",2,2,"BAC SS 2009 — Géographie — Coeff 2 — 2h\nQuelles sont les caractéristiques fondamentales de la population brésilienne ?"),
("SS",2009,"Économie",2,2,"BAC SS 2009 — Économie — Coeff 2 — 2h\nRôle et place des activités économiques dans le développement des pays sous-développés. Montrez que l'insuffisance des investissements est l'une des causes fondamentales du sous-développement."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2008 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2008,"Français",4,4,"BAC SS 2008 — Français — Coeff 4 — 4h\n« Quel rôle la littérature peut-elle jouer dans le développement de l'Afrique ? »"),
("SS",2008,"Philosophie",3,3,"BAC SS 2008 — Philosophie — Coeff 3 — 3h\nLe droit à l'expression autorise-t-il à tout dire ? Discutez."),
("SS",2008,"Anglais",3,3,"BAC SS 2008 — Anglais — Coeff 3 — 3h\nTexte : La Tortue et l'Aigle. Compléter avec (Refused/enjoying/dissatisfied/can/birds/sat/day/tortoise). Compréhension. Grammaire. Essai."),
("SS",2008,"Géographie",2,2,"BAC SS 2008 — Géographie — Coeff 2 — 2h\nLa révolution verte a permis d'éviter la famine en Inde. Comment ce pays s'y est-il pris ?"),
("SS",2008,"Économie",2,2,"BAC SS 2008 — Économie — Coeff 2 — 2h\nRôle et importance de l'industrie dans le développement socio-économique d'un pays. Malgré ses atouts, pourquoi la Guinée reste-t-elle sous-développée ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2007 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2007,"Français",4,4,"BAC SS 2007 — Français — Coeff 4 — 4h\nSpinoza : « L'homme qui est conduit par la raison est plus libre dans la société où il vit selon la loi commune que dans la solitude, où il n'obéit qu'à lui-même. » Que pensez-vous de cette affirmation ?"),
("SS",2007,"Philosophie",3,3,"BAC SS 2007 — Philosophie — Coeff 3 — 3h\nClaude Bernard : « Le fait suggère l'idée, l'idée dirige l'expérience, l'expérience juge l'idée. » Expliquez cette affirmation."),
("SS",2007,"Anglais",3,3,"BAC SS 2007 — Anglais — Coeff 3 — 3h\nI. Lettre d'une ONG de Siguiri demandant une assistance financière pour construire une école (3 salles de classe). Compréhension (5pts). II. Compléter des conditionnels hypothétiques. III. Essai."),
("SS",2007,"Géographie",2,2,"BAC SS 2007 — Géographie — Coeff 2 — 2h\nLa République de Guinée est le Château d'Eau de l'Afrique de l'Ouest.\nMontrez-le en insistant sur l'importance socio-économique des États de la sous-région. (Carte obligatoire)"),
("SS",2007,"Économie",2,2,"BAC SS 2007 — Économie — Coeff 2 — 2h\nIl est démontré que l'explosion démographique handicape sérieusement le développement des pays pauvres. Que faut-il faire pour freiner ce phénomène ? Justifiez à l'aide d'exemples précis."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2006 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2006,"Français",4,4,"BAC SS 2006 — Français — Coeff 4 — 4h\nI. Paul Éluard : « le poète est davantage celui qui inspire bien plus que celui qui est inspiré. »\nII. « C'est une erreur profonde de porter une œuvre littéraire au cinéma. » Discutez ce point de vue en vous appuyant sur une œuvre de Sembène Ousmane ou tout autre écrivain africain."),
("SS",2006,"Philosophie",3,3,"BAC SS 2006 — Philosophie — Coeff 3 — 3h\n« Les sciences humaines décrivent-elles l'homme comme un animal prévisible ? » Expliquez cette affirmation."),
("SS",2006,"Anglais",3,3,"BAC SS 2006 — Anglais — Coeff 3 — 3h\nCompléter une histoire au passé (Fatou Kaba à Londres) avec les verbes corrects. Exercices HOW MUCH/MANY/LONG/OFTEN/FAR. Essai."),
("SS",2006,"Géographie",2,2,"BAC SS 2006 — Géographie — Coeff 2 — 2h\nLa fédération de Russie est née de l'explosion de l'URSS.\n1) Présentez-la (aspects physiques et humains). 2) Décrivez ses problèmes démographiques. 3) Expliquez pourquoi la question des nationalités menace la Russie."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2005 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2005,"Français",4,4,"BAC SS 2005 — Français — Coeff 4 — 4h\nMontaigne : « La force et la violence peuvent quelque chose mais pas toujours tout. »\nJustifiez cette pensée en vous servant de l'actualité."),
("SS",2005,"Philosophie",3,3,"BAC SS 2005 — Philosophie — Coeff 3 — 3h\nMontaigne : « La force et la violence peuvent quelque chose mais pas toujours tout. »\nJustifiez cette pensée de Montaigne en vous servant de l'actualité."),
("SS",2005,"Anglais",3,3,"BAC SS 2005 — Anglais — Coeff 3 — 3h\nTexte : L'Orpheline et la Chèvre (Hadjaratou et sa belle-mère). Compléter avec (the elderly Nana/inheritance/guard/step-mother/chores/charming goat/step-sister/surprised). Compréhension. Grammaire. Essai."),
("SS",2005,"Économie",2,2,"BAC SS 2005 — Économie — Coeff 2 — 2h\nDans le cadre du développement économique des pays membres de la CEDEAO, dégagez les différents types d'intégration et dites lequel est le mieux indiqué pour eux."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2004 — 3/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2004,"Français",4,4,"BAC SS 2004 — Français — Coeff 4 — 4h\n« Aussi prodigieuses que soient ses inventions et ses découvertes, la science reste toujours une œuvre humaine qui n'a pu éliminer la foi. »\nDémontrez la véracité de cette affirmation d'un penseur."),
("SS",2004,"Philosophie",3,3,"BAC SS 2004 — Philosophie — Coeff 3 — 3h\n« Aussi prodigieuses que soient ses inventions et ses découvertes, la science reste toujours une œuvre humaine qui n'a pu éliminer la foi. »\nDémontrez la véracité de cette affirmation d'un penseur."),
("SS",2004,"Économie",2,2,"BAC SS 2004 — Économie — Coeff 2 — 2h\nA travers une analyse soutenue, montrez qu'en dépit de la forte proportion de la population active dans l'agriculture, ce secteur reste faible dans les pays du tiers monde. Dégagez les causes et les conséquences de cette faiblesse."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2003 — 1/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2003,"Économie",2,2,"BAC SS 2003 — Économie — Coeff 2 — 2h\nL'exploitation financière constitue à l'époque moderne l'un des traits dominants des rapports de dépendance et de domination des monopoles capitalistes sur les pays du Sud.\nDégagez les raisons qui motivent les pays développés à investir dans les pays sous-développés. Quelles sont les conséquences de ce phénomène ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2002 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2002,"Français",4,4,"BAC SS 2002 — Français — Coeff 4 — 4h\nBlaise Cendrars : « La publicité est la plus belle expression de notre époque ; la grande nouveauté du jour, un art. »\nExpliquez, comment et s'il faut, discutez cette opinion."),
("SS",2002,"Philosophie",3,3,"BAC SS 2002 — Philosophie — Coeff 3 — 3h\nLe progrès, les recherches scientifiques devraient continuer à améliorer le sort de l'ensemble des êtres humains. Pourtant, dans ce domaine, les inégalités persistent voire s'accentuent entre le nord et le sud.\nExpliquez et commentez."),
("SS",2002,"Géographie",2,2,"BAC SS 2002 — Géographie — Coeff 2 — 2h\nLa République de Guinée repose sur de vastes terres cultivables ; mais le pays importe des millions de tonnes de riz.\n1. Dégagez les conditions naturelles et économiques de l'agriculture.\n2. Pourquoi la production du riz ne couvre-t-elle pas les besoins nationaux ?\n3. Indiquez les principales cultures vivrières et industrielles du pays et localisez-les sur la carte."),
("SS",2002,"Économie",2,2,"BAC SS 2002 — Économie — Coeff 2 — 2h\nCause de la faiblesse de l'agriculture et conséquence socio-économique dans les pays sous-développés. Proposez des solutions."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2001 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2001,"Français",4,4,"BAC SS 2001 — Français — Coeff 4 — 4h\n« Nous ne lisons jamais pour oublier la vie, au contraire pour l'éclairer. Les livres nous aident à voir, à agir, à vivre. » Expliquez."),
("SS",2001,"Philosophie",3,3,"BAC SS 2001 — Philosophie — Coeff 3 — 3h\nMontesquieu : « Pour jouir de la liberté, il faut que chacun puisse dire ce qu'il pense. Et pour la conserver, il faut encore que chacun puisse dire ce qu'il pense. »"),
("SS",2001,"Géographie",2,2,"BAC SS 2001 — Géographie — Coeff 2 — 2h\nMontrez l'importance des ressources minières et énergétiques de la République de Guinée et dégagez la perspective industrielle du pays."),
("SS",2001,"Économie",2,2,"BAC SS 2001 — Économie — Coeff 2 — 2h\nExpliquez comment l'échange inégal constitue un fléau au progrès des pays en voie de développement."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SS 2000 — 1/7
# ══════════════════════════════════════════════════════════════════════════════
("SS",2000,"Économie",2,2,"BAC SS 2000 — Économie — Coeff 2 — 2h\nL'intégration économique s'avère être la meilleure voie du développement des pays africains.\nExpliquez et justifiez cette affirmation. Montrez comment la CEDEAO peut contribuer au développement de l'Afrique de l'Ouest."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SE 2020 — COMPLET 7/7
# ══════════════════════════════════════════════════════════════════════════════
("SE",2020,"Biologie-Géologie",4,4,"""BAC SE 2020 — Biologie-Géologie — Coeff 4 — 4h
BIOLOGIE (15pts) :
I — Méiose : prophase réductionnelle, tétrades, échange de fragments.
ADN matrice 1 : TACCGTACCTTTGGC → protéine 1 : Met-Ala-Try-Gly-Ser.
ADN matrice 2 : TACGGATCTCCCAGG → protéine 2 : Met-Pro-Arg-Lys-Pro.
a) Séquences attendues. b) Phénomène précis. c) Séquence des ADN après prophase.
Codes : GCA=Ala; CCG=Pro; UGG=Try; AAA=Lys; AUG=Met; GGG=Gly; CCU=Pro; AGA=Arg; UCC=Ser.
II — Synapse chimique : recapture/influx centripète/entrée Ca²+/libération/influx centrifuge/fixation du neurotransmetteur. Chronologie. Schéma. Loi de conductibilité.
III — Transmission gènes piebald (p) et hairless (h). F1 uniformes sans chute de poils. 75 tachetés sans chute/8 uniformes sans chute/10 tachetés avec chute/77 uniformes avec chute. Loi de Mendel. Dominance. Localisation des gènes.
IV — Couturier enfile aiguille. Rétine : localisation image. Schéma annoté.
GEOLOGIE (5pts) :
1) Plaques P1 (d1) et P2 (d2>d1). Nommer. Quelle plaque chevauche ? Pourquoi ? Nom du mouvement.
2) Pétrole/empreintes/restes d'organismes/fossiles momies. Processus de fossilisation."""),
("SE",2020,"Mathématiques",3,3,"""BAC SE 2020 — Mathématiques — Coeff 3 — 3h
Exercice (8pts) : (E) dans C : 4z³-6i√3z²-3(3+i√3)z-4=0.
1) Racines carrées de 6+6i√3. 2) Résoudre 2z²-(1+3i√3)z-4=0.
3a) Développer (2z+1)(2z²-(1+3i√3)z-4). 3b) Solutions de (E).
4) z0=-½ ; z1=-½+i√3/2 ; z2=1+i√3. Forme trigonométrique.
Problème (12pts) : f(x)=x+lnx/x sur ]0;+∞[, courbe (C), unité 3cm.
g(x)=x²+1-lnx : variations sur ]0;+∞[ et signe.
Limites de f en 0 et +∞. Asymptote D : y=x. f'(x). Sens de variation. Tableau.
Point A : tangente parallèle à D. Tracer D, T et (C)."""),
("SE",2020,"Physique",3,3,"""BAC SE 2020 — Physique — Coeff 3 — 3h
Théorie : Cosmonaute en impesanteur. Loi de Lorentz.
1) Ions de même charge q et masses m1, m2, accélérés par tension U0.
EC1, EC2. P1, P2. Trajectoire dans champ électrique orthogonal. Séparation dans champ magnétique B.
2) Automobiliste 120km/h. Motard MRUV → 100km/h en 10s. Durée poursuite. Distance. Vitesse motard quand il rattrape.
3) Circuit bobine (R2,L1) série + R2=12,5Ω. I=3,2A, U=64V, U1=U2. Z1=Z2. Diagramme de Fresnel.
ϕ, R1, Lω. Fréquence (L=36mH). cos(36,8°)=0,8."""),
("SE",2020,"Chimie",3,3,"BAC SE 2020 — Chimie — Coeff 3 — 3h\n(Même sujet que BAC SM/SE 2020)\nDécomposition H2O2. Cinétique. Acide méthanoïque. Indicateur coloré."),
("SE",2020,"Français",2,2,"BAC SE 2020 — Français — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2020)\nPasteur (1888) : loi de sang et de mort vs loi de paix et de salut."),
("SE",2020,"Anglais",2,2,"BAC SE 2020 — Anglais — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2020)\nTableau comparatifs, nombres, transformation de phrases, essai sur l'éducation."),
("SE",2020,"Philosophie",2,2,"BAC SE 2020 — Philosophie — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2020)\nEinstein : « Le progrès technique est comme une hache... »"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SE 2019 — 5/7
# ══════════════════════════════════════════════════════════════════════════════
("SE",2019,"Physique",3,3,"""BAC SE 2019 — Physique — Coeff 3 — 3h
A. Théorie : Mise en évidence du champ magnétique (schéma). Règle du flux maximal.
B. Pratique :
1. Satellite h=1000km. Vitesse dans référentiel géocentrique. Durée T. RT=6400km; g0=9,8m/s²; √1,324=1,15.
2. Rail MN=10cm, R=0,6Ω. Barre Cu 20cm en 0,1s. B=1,5T vertical. Flux, f.é.m., courant, force Laplace, puissances.
3. Young a=1mm, D=1m, 10 interfranges=5,9mm. Numéros et nature. Calculer λ. Couleur."""),
("SE",2019,"Chimie",3,3,"BAC SE 2019 — Chimie — Coeff 3 — 3h\n(Même sujet que BAC SM/SE 2019)\nSolution tampon pH=9,2. Estérification + autocatalyse. Chlorure d'acyle RCOCl."),
("SE",2019,"Français",2,2,"BAC SE 2019 — Français — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2019)\nJean Onimus sur la poésie libératrice dans la société mécanisée."),
("SE",2019,"Anglais",2,2,"BAC SE 2019 — Anglais — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2019)\nTemps verbaux, tag questions, comparatives, paragraph."),
("SE",2019,"Philosophie",2,2,"BAC SE 2019 — Philosophie — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2019)\nEst-il légitime de recourir à la violence pour défendre ses droits ?"),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SE 2018 — 4/7
# ══════════════════════════════════════════════════════════════════════════════
("SE",2018,"Biologie-Géologie",4,4,"""BAC SE 2018 — Biologie-Géologie — Coeff 4 — 4h
BIOLOGIE (15pts) :
I — Hérédité : homme sain × femme saine → fille saine → (croisement) → fille malade + 3 garçons sains.
Arbre généalogique. Allèle dominant ou récessif ? Autosome ou gonosome ? Génotype fille malade.
II — Grenouille spinale suspendue. Pincement nerf sciatique → mouvement pied. Analyse nerf et muscle.
Adéquation de différents stimuli. Organes arc réflexe médullaire. Schéma arc réflexe inné.
III — Puberté. Castration adulte → stérilité + régression. Injection testostérone → maintien/développement. Commande des modifications pubertaires.
IV — Phagocytose : cellules englobent bactéries, digèrent. Nom de la réaction. Cellules. Étapes. Schéma.
GEOLOGIE (5pts) :
1) Phylogénie : Homo sapiens néanderthalensis / Australopithèques graciles et robustes / Homo sapiens sapiens / Lucy / Homo habilis / Homo erectus.
2) Asthenosphère : couche déformable entre 70 et plusieurs centaines de km. Nommer. Couches au-dessus."""),
("SE",2018,"Mathématiques",3,3,"""BAC SE 2018 — Mathématiques — Coeff 3 — 3h
Exercice (8pts) : Suite (Un), U0=0, U_(n+1)=½U_n+1.
Calculer U1, U2, U3. V_n=U_n-2 : géométrique raison ½. V_n puis U_n. S_n puis T_n.
Problème (12pts) : f(x)=x²/2×(ln(x)-3/2) sur [0;+∞[, f(0)=0.
Dérivabilité en 0. Tableau de variation. Courbe (C), unité 2cm.
Point A d'abscisse 1. Tangente T. φ(x)=f(x)+x-1/4. φ'(x). Signe de φ. Position de (C) par rapport à (T). Tracer."""),
("SE",2018,"Physique",3,3,"""BAC SE 2018 — Physique — Coeff 3 — 3h
Théorie : Plan incliné sans frottement. v² après parcours X (énergie cinétique). Accélération par RFD.
1) Sr-90 émetteur β⁻, T=28 ans. Equation désintégration. Définition de T.
   Nourrisson absorbe m0=1,0µg. Masse à 28 ans et 56 ans.
2) X=3t, Y=-4t²+5t. Equation cartésienne trajectoire. Vitesse à ordonnée max. Abscisse quand Y=0. Vitesse à t=6s.
3) GBF U=24V, f=180Hz. Bobine r=120Ω, L=250mH. Construction de Fresnel. I_eff. Phase."""),
("SE",2018,"Anglais",2,2,"BAC SE 2018 — Anglais — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2018)\nTexte sur l'attaque de Conakry (1970). Exercices de grammaire. Essai."),

# ══════════════════════════════════════════════════════════════════════════════
#  BAC SE 2017 — 6/7
# ══════════════════════════════════════════════════════════════════════════════
("SE",2017,"Biologie-Géologie",4,4,"""BAC SE 2017 — Biologie-Géologie — Coeff 4 — 4h
GEOLOGIE (5pts) :
1) Plaques P1 et P2 s'affrontent. Zone Z : séismes violents et soulèvement (montagnes). Localiser Z. Nommer P1 et P2. Type de mouvement.
2) Zones marines selon éloignement des côtes : salinité, luminosité.
BIOLOGIE (15pts) :
I — Cobayes : lignée noire lisse × lignée blanche hirsute. F1 noirs hirsutes. Pourquoi ≠ parents ? Génotypes.
II — Dosage hormones ovariennes (28 mars→27 avril) toutes les 5 jours.
Oestrogènes (mg/l) : 2/9/16/10/14/13/2. Progestérone (mg/l) : 0,5/0,5/0,5/1/7/10/0,5.
Graphes des deux courbes. Dater les événements importants du cycle. État physiologique le 27 avril. Action de la progestérone sur l'utérus.
III — Rein (1 million de néphrons/rein). Tableau concentrations plasma/urine primitive/urine définitive.
Définir néphron. Schéma annoté. Comparer plasma/urine primitive et urine primitive/urine définitive. Mettre en évidence glucose et chlorures.
IV — N1 (chronaxie 0,5ms) et N2 (chronaxie 1ms), même rhéobase 2mV. Lequel est le plus excitable ?"""),
("SE",2017,"Mathématiques",3,3,"""BAC SE 2017 — Mathématiques — Coeff 3 — 3h
Exercice (8pts) : Sac de 10 objets : n noirs, (10-n) blancs. Tirage simultané de 2.
P(deux couleurs différentes) ? P(deux noirs) ? P(deux blancs) ? Calculer n pour P(deux blancs)=7/15.
Problème (12pts) : f(x)=lnx/(1+lnx), courbe (C), unité 2cm.
Ensemble Df. a et b tels que f(x)=a+b/(1+lnx). Limites aux bornes. Dérivée f'. Tableau.
Résoudre f(x)=1/2. Tangente (T) au point d'ordonnée 1/2. Construire (T) et (C)."""),
("SE",2017,"Physique",3,3,"""BAC SE 2017 — Physique — Coeff 3 — 3h
Théorie : Principe Fondamental de la Dynamique (RFD). Définir : interférences lumineuses, radioactivité, effet photoélectrique. Mise en évidence de l'induction électromagnétique.
I — "Boro d'enjaillement" : élève V=8m/s court après bus a=2m/s², distance D=18m.
Equations horaires. Distance entre mobiles à t=2s. L'élève réussit-il si écart ≤1m ?
II — Dipôle RLC série : Equation du circuit. φ (U=50V, N=50H, L=1H, r=10Ω, R=300Ω, C=5×10⁻⁶F).
Impédance Z. I_eff. Expression i(t). Déphasage tension bobine/i(t).
III — Cathode césium. λ=0,80µm, seuil λ0=0,66µm. Indication ampèremètre.
Avec λ=0,30µm : domaine spectral. Energie photon. Travail d'extraction. Vitesse max des électrons."""),
("SE",2017,"Chimie",3,3,"BAC SE 2017 — Chimie — Coeff 3 — 3h\n(Même sujet que BAC SM/SE 2017)\nAcide dichloroalcanoïque. Estérification acide propénoïque + éthanol. Vitesse de formation."),
("SE",2017,"Anglais",2,2,"BAC SE 2017 — Anglais — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2017)\nsome/any, nombres, comparatifs/superlatifs."),
("SE",2017,"Philosophie",2,2,"BAC SE 2017 — Philosophie — Coeff 2 — 2h\n(Même sujet que BAC SM/SE 2017)\nEinstein sur le progrès technique."),


# ══════════════════════════════════════════════════════════════════════════════
#  BAC SM 2011 → 2000 — 59 sujets récupérés depuis exam224.com
# ══════════════════════════════════════════════════════════════════════════════
("SM",2011,"Mathématiques",4,4,"""BAC SM 2011 — Mathématiques — Coeff 4 — 4h
A) Numération base a : A=211, B=312, C=133032.
1. Montrer a>3. 2a) C=A×B → a³-3a²-2a-8=0, a divise 8. b) Déterminer a.
3. Écrire 214 en base 4. 4a) A,B,C en décimal avec a=4. b) C=A×B=PPCM(A,B); 37x+54y=1 → (19,-13) solution.
B) Moussa atteint 5 lièvres/6, Mamadou 4/5.
1. P(lièvre tué si tirent ensemble). 2a) Mamadou tire le premier ; Moussa : chances réduites de moitié si Mamadou manque. P(Moussa tue). 2b) P(lièvre s'échappe).
C) g(x)=x+√(x²+1). Df. g(x)>x+|x|. Signe de g.
Variations. Courbe. φ(x)=ln(x+√(x²+1)).
Résoudre φ(x)=-ln(3-2√2). φ impaire. φ bijection R→R. φ((eⁿ-e⁻ⁿ)/2)=n.
I_n=∫[nπ;(n+1)π]f(x)dx."""),
("SM",2011,"Physique",3,3,"""BAC SM 2011 — Physique — Coeff 3 — 3h
Théorie : Chute libre. Oscillateur élastique. Lois conservation désintégration nucléaire.
I. RLC série, U=12V, f=50Hz. U_B=10,2V, U_C=16V, I=0,6A. Z_C, Z_B, Z. R et L de la bobine.
II. Tableau mouvement rectiligne : t=[0;0,1;...;1]s, x=[5;15;29;47;69;95;124,5;154,5;184,5;214,5;244,5]cm.
Phase MRUV : accélération, équation. Phase MU : équation horaire."""),
("SM",2011,"Chimie",3,3,"""BAC SM/SE 2011 — Chimie — Coeff 3 — 3h
I. HCl (2×10⁻²mol/L) + NaOH (10⁻²mol/L) : 10cm³ chacun. Équation bilan. Équivalence atteinte ? pH. Concentrations des espèces. log5=0,7.
II. 1g Mg dans 30cm³ HCl (0,1mol/L). Tableau cinétique [H₃O⁺] à t=0,1,2,3,4,5min : 1,0 ; 0,50 ; 0,355 ; 0,25 ; 0,16 ; 0,10 (×10⁻¹mol/L). Concentration Mg²⁺ aux t=2min et t=4min. Vitesse moyenne formation Mg²⁺.
III. Produit A → (oxydation KMnO₄) → B (pH<7) → C = CH₃-CH₂-COCl (chlorure d'acyle). C + NH₃ → HCl + D (amide). C + A → HCl + E (ester). Équations. Formules et noms de A, B, D, E."""),
("SM",2011,"Français",2,2,"""BAC SM/SE 2011 — Français — Coeff 2 — 2h
Gandhi : « La règle d'or de la conduite est la tolérance mutuelle, car nous ne penserons jamais tous de la même façon ; nous ne verrons qu'une partie de la vérité et sous des angles différents. » Expliquez et commentez."""),
("SM",2011,"Anglais",2,2,"""BAC SM/SE 2011 — Anglais — Coeff 2 — 2h
I. Remise en ordre de la Pyramide de Chéops (jumbled sentences). II. Conditionnels (2e conditionnel). III. Questions WH. IV. Transformation de temps verbaux (Past Perfect, Simple Present, etc.)."""),
("SM",2011,"Économie",2,2,"""BAC SM 2011 — Économie — Coeff 2 — 2h
Le sous-développement des uns dit-on est une conséquence du développement des autres. Expliquez."""),
("SM",2010,"Mathématiques",4,4,"""BAC SM 2010 — Mathématiques — Coeff 4 — 4h
Exercice 1 : Récurrence : Σk²(k-1) pour entier n non nul. PGCD(A(n),B(n)) si n multiple de 3. Vérifier n=21.
B) Condensateur C=5µF, V₀=200V. Charge à t=0. Énergie. Fréquence propre. Intensité maximale.
Plan incliné α=30°, m=500g, |R| constante, β. Accélération. a si g=10, parcours r=15m en t=2s. Angle β et norme de R.
Polonium-210 → Pb + α. Déterminer a, b, X. Type de radiation. Énergie en MeV. Vitesse α.
Young a=1mm, D=2m, λ=400nm. Interfrange. Nature frange centrale."""),
("SM",2010,"Physique",3,3,"""BAC SM 2010 — Physique — Coeff 3 — 3h
I. Interférences Young : f=5,093×10¹⁴Hz, δ=5,89µm. λ. Phase ou opposition?
II. Satellite orbite circulaire altitude h. Mouvement uniforme. V=f(R_T,h,g₀). Période T. T²/(R_T+h)³=constante. g₀=10m/s², R_T=6400km, h=1000km. V et T.
III. RC série, P=100W, U=120V, f=50Hz, I=2A. R. Impédance. Facteur de puissance. Capacité C.
Th-227→Rn par α. Définir radioactivité α. Équation bilan."""),
("SM",2010,"Chimie",3,3,"""BAC SM/SE 2010 — Chimie — Coeff 3 — 3h
I. Amine aliphatique saturée A, 19,2% d'azote. Formule brute. Formules semi-développées et noms des isomères. A est chirale : stéréoisomères. Solution A (8×10⁻²mol/L), pH=11,8 → constante d'acidité.
II. 20cm³ KMnO₄ + 30cm³ acide éthanoïque (5×10⁻²mol/L). Équation bilan. Quantité n(MnO₄⁻). Acide non oxydé.
III. 10cm³ HCl (0,3mol/L) + 15cm³ NH₃ (0,2mol/L). pH=5,1. Concentrations espèces. pKA(NH₄⁺/NH₃). Volume HCl (0,1mol/L) pour demi-équivalence (NH₃ 5×10⁻²mol/L, 10cm³)."""),
("SM",2010,"Économie",2,2,"""BAC SM 2010 — Économie — Coeff 2 — 2h
Le transport occupe une place importante dans la vie socio-économique des nations.
Dégagez à l'aide d'exemples précis l'importance et la vocation des voies de transport dans le processus de développement."""),
("SM",2009,"Mathématiques",4,4,"""BAC SM 2009 — Mathématiques — Coeff 4 — 4h
A) PGCD(231,3311) par algorithme d'Euclide.
B(n)=1²+2²+...+n² = n(n+1)(2n+1)/6 par récurrence. Si n multiple de 3 : PGCD(A(n),B(n)). Vérifier n=21.
B) Rendez-vous : 5 personnes, 5 cafés. P(tous cafés différents). P(tous au même café). P(au moins 2 au même café).
C) f sur R₊ : variations, courbe. (Contenu en images base64 dans original)"""),
("SM",2009,"Physique",3,3,"""BAC SM 2009 — Physique — Coeff 3 — 3h
I. Condensateur C=5µF, V₀=200V. Charge à t=0. Énergie. Fréquence propre des oscillations. Intensité maximale.
II. Plan incliné α=30°, m=500g. Expression vecteur accélération. Distance=15m en t=2s → accélération. Angle β et norme de R.
III. Polonium-210 → Pb(a)(b) + X. Déterminer a, b, X. Type de radiation. Énergie en MeV. Vitesse particule X. Données : M_Po=210,0482u, M_Pb=206,0385u, m_α=4,0015u, 1u=931,5MeV/C².
IV. Young a=1mm, D=2m, λ=400nm. Interfrange. Nature frange centrale."""),
("SM",2009,"Chimie",3,3,"""BAC SM/SE 2009 — Chimie — Coeff 3 — 3h
A-Théorie : Catalyse homogène vs hétérogène. 2 exemples chaque. Synthèse HCl et monochloration CH₄ (mécanisme, lumière).
B-Pratique : 0,37g acide propanoïque dans 100ml. Concentration. pH=3,1 → acide faible. Équation ionisation. Mélange 20ml+25ml NaOH (0,02mol/L) → pH=4,9 → pKA.
Données : 10⁻³,¹=8×10⁻⁴ ; 10⁰,¹=1,25.
Acide carboxylique A + alcool B (M=46g/mol). Formule B. Estérification. M(ester)=88g/mol → formule exacte. Isomères de l'ester. Comparer action A+B vs chlorure d'acyle+B."""),
("SM",2009,"Français",2,2,"""BAC SM/SE 2009 — Français — Coeff 2 — 2h
Andrée Jules : « Se libérer n'est rien, l'ardu (le difficile) est savoir être libre. » Expliquez et commentez."""),
("SM",2009,"Anglais",2,2,"""BAC SM/SE 2009 — Anglais — Coeff 2 — 2h
I. Questions correspondant à des réponses (Mont Nimba, Billo, Paris, Indépendance 1958, absent).
II. Phrase correspondant aux tag questions (does she? were they? wouldn't you? will he?).
III. Remettre en ordre des mots. Jumbled letters (jobs/verbs). Dialogues avec modalités (must, should, can)."""),
("SM",2009,"Économie",2,2,"""BAC SM 2009 — Économie — Coeff 2 — 2h
A. L'exploitation financière est l'une des causes manifestes du retard des économies des pays sous-développés. Mécanisme. Solutions.
B. Quelle stratégie un pays en voie de développement peut utiliser pour résoudre le problème de chômage ?"""),
("SM",2008,"Mathématiques",4,4,"""BAC SM 2008 — Mathématiques — Coeff 4 — 4h
A) Trouver paires (a,b) d'entiers naturels vérifiant une relation donnée. (Contenu en images base64)
Résolution d'équations dans Z². Suite (Un). Proba : 4 médecins, 4 habitants. Barycentres.
Problème : Variations de f. Asymptote oblique. Tangente. (Contenu partiel en images)"""),
("SM",2008,"Physique",3,3,"""BAC SM 2008 — Physique — Coeff 3 — 3h
I. Solénoïde l=80cm, r=3cm, fil d=0,8mm, ρ=8×10⁻⁸Ω.m. Calculer R et L.
i=f(t) pour u=5sin(3000t). Donné tan(0,444)=0,417rad.
II. Automobile 126km/h. Obstacle à D=100m. Freine : 90km/h en Δt=1,6s.
1. Décélération. 2. Distance d'arrêt sans réaction. 3. Distance d'arrêt avec temps de réaction 1s."""),
("SM",2008,"Chimie",3,3,"""BAC SM/SE 2008 — Chimie — Coeff 3 — 3h
I. Carbure d'hydrogène à liaison multiple + H₂ (saturation). Formule générale. 0,85g NH₃ + 2,1g carbure → composé saturé A. Formule brute, M exact, nom. Isomères. Masse de A obtenue (3,4g NH₃).
Solution A (1,18g/L) titrée HCl (2×10⁻²mol/L). Équation bilan. Volume réagi.
II. HCl (3×10⁻¹mol/L, 10ml) + NH₃ (2×10⁻¹mol/L, 15ml). pH=5,1. Espèces chimiques et concentrations. KA. Volume HCl (0,1mol/L) pour demi-équivalence (NH₃ 5×10⁻²mol/L, 10cm³)."""),
("SM",2008,"Français",2,2,"""BAC SM/SE 2008 — Français — Coeff 2 — 2h
Albert Camus (La Peste) : « Tout est permis cela ne veut pas dire que rien n'est défendu. » Expliquez, commentez et discutez."""),
("SM",2008,"Anglais",2,2,"""BAC SM/SE 2008 — Anglais — Coeff 2 — 2h
Stone Soup : Compléter les lacunes (put/woman/your/the/but/a). Références pronominaux. Opinion en 20 mots.
Questions de compréhension. Phrases avec since/for."""),
("SM",2008,"Économie",2,2,"""BAC SM 2008 — Économie — Coeff 2 — 2h
La FAO indique que la production céréalière a diminué en 2008. Montrez les conséquences de cette situation et proposez des solutions."""),
("SM",2007,"Mathématiques",4,4,"""BAC SM 2007 — Mathématiques — Coeff 4 — 4h
A) Σk²(k-1) pour n entier naturel non nul = (n-1)n(n+1)/6. Décomposer 469 en facteurs premiers. Résoudre x³-y³=469 dans N².
B) 3 médecins, 4 habitants malades. P(un seul médecin appelé). P(3 médecins appelés).
C) f(x)=(1-x)(1+eˣ). Limites. Asymptote D:y=-x+1. Position relative (C) et (D). Variations de f'. Tracer (C). (Suite en images base64)"""),
("SM",2007,"Physique",3,3,"""BAC SM 2007 — Physique — Coeff 3 — 3h
1. Système de 3 masses identiques m aux sommets d'un triangle équilatéral de côté l.
Centre d'inertie de AB. Centre d'inertie des 3 masses. Prévision.
2. Séries spectrales H : 1/λ=R_H(1/n₁²-1/n₂²), R_H=1,0973×10⁷m⁻¹.
Domaine visible [0,4µm;0,8µm] → n₁=2. Nombre de raies. Longueurs d'onde.
λ pour n₁=1,n₂=2 et n₁=3,n₂=1. Domaines spectraux.
3. Enfant V=4m/s, ballon m=800g, V=-10m/s. Sens et vitesse après blocage. Après renvoi (10m/s), vitesse enfant (m_enfant=50kg)."""),
("SM",2007,"Chimie",3,3,"""BAC SM/SE 2007 — Chimie — Coeff 3 — 3h
I. a) Volumes NH₃ (10⁻²mol/L) et NH₄Cl (même C) pour 100ml à pH=9,4. pKA(NH₄⁺/NH₃)=9,2. Concentrations des espèces. Données : 10⁻⁹,⁴=4×10⁻¹⁰ ; 10⁰,¹⁵=1,41.
II. Acide carboxylique A + alcool B (M=46g/mol) → ester C (M=88g/mol). Équation bilan. B : M=46, oxydation→Fehling+. Formules B et C. Anhydride D. Différences A+B vs D+B. Masse produits si 15g D + 6g B, rendement 70%. Réactif en excès."""),
("SM",2007,"Français",2,2,"""BAC SM/SE 2007 — Français — Coeff 2 — 2h
Pascal : « La justice sans la force est impuissante, la force sans la justice est tyrannique. » Expliquez et commentez."""),
("SM",2007,"Anglais",2,2,"""BAC SM/SE 2007 — Anglais — Coeff 2 — 2h
Texte sur l'anglais langue internationale : remplir lacunes (understand/people/business/world/both/international/learn/communicate/example/listen/ignore/country). Vrai/Faux. Questions correspondantes à des réponses. Distances et fréquences (Coyah, Kankan, Pépé Diéké, Février)."""),
("SM",2007,"Économie",2,2,"""BAC SM 2007 — Économie — Coeff 2 — 2h
Il est démontré que l'explosion démographique est un handicap sérieux pour le développement des pays pauvres. Que faut-il faire pour freiner ce phénomène ? Justifiez avec des exemples précis."""),
("SM",2006,"Mathématiques",4,4,"""BAC SM 2006 — Mathématiques — Coeff 4 — 4h
A) Jury 3/7 (4H+3F). X = nombre de femmes. Loi de X, E(X). P(au moins 1 femme).
B) 1. Ensemble des entiers relatifs x tels que 8x≡7[5]. 2. Résoudre 336x+210y=294 dans Z².
C) A(1;5), B(2;3), C(4;4). Barycentre G_α avec coefficients 1, α+1, -α+3. Ensemble de G_α. G_α=D(1;3) → α. Pour α=5 : ensemble M tels que MA²+6MB²-2MC²=25.
D) f(x)=(1-x)(1+eˣ). Limites aux bornes. Asymptote D:y=-x+1. Position relative. Variations de f'. Tracer (C)."""),
("SM",2006,"Physique",3,3,"""BAC SM 2006 — Physique — Coeff 3 — 3h
A-Théorie : Loi de Lenz. 3 lois de Kepler + apesanteur. Interférences lumineuses. Applications effet photo-électrique.
B-Problème : RLC série : C, L (de résistance R, pulsation ω). 3 tensions efficaces égales (bornes GBF, condensateur, bobine). L=f(R,ω) et C=f(R,ω). Application numérique R=5Ω, f=50Hz. Déphasage φ si fréquence modifiée."""),
("SM",2006,"Chimie",3,3,"""BAC SM/SE 2006 — Chimie — Coeff 3 — 3h
I. NH₃ + eau → solution 0,1mol/L. Équation. Volume NH₃ pour 200ml. pH=11 → concentrations espèces.
II. 0,59g monoamine primaire saturée + 20ml HCl (0,5mol/L) → équivalence. Équation bilan. Masse molaire. Formule moléculaire. Formules semi-développées et noms."""),
("SM",2006,"Français",2,2,"""BAC SM/SE 2006 — Français — Coeff 2 — 2h
Jean Didil : « L'Afrique ne se développe pas, elle est développée par l'extérieur avec la complicité de ses enfants. » Expliquez et discutez."""),
("SM",2006,"Anglais",2,2,"""BAC SM/SE 2006 — Anglais — Coeff 2 — 2h
Remettre dans l'ordre les phrases (Mariama et Papi). Identifier la faute grammaticale (A,B,C,D) dans chaque phrase. Questions correspondant à des réponses."""),
("SM",2005,"Mathématiques",4,4,"""BAC SM 2005 — Mathématiques — Coeff 4 — 4h
A) Diviseurs de 5929. PGCD et PPCM solutions de x²-91x+588=0 → couples (a,b) dans N. 
Démontrer A=3^(3n+2)+2^(n+4) divisible par 5.
B) Suite (Un) : définition par récurrence (en images base64 dans original). Limite et somme."""),
("SM",2005,"Physique",3,3,"""BAC SM 2005 — Physique — Coeff 3 — 3h
I-Théorie : Diffraction de la lumière. Applications effet photo-électrique. Notion d'impesanteur.
II-Problèmes :
1. Bobine inductance négligeable + C=50µF → f=440Hz. Calculer L.
2. Solénoïde 400 spires, Ø=10cm, I=10A, B=10⁻²T perpendiculaire. Action de B. Travail forces électromagnétiques.
3. Boule m=10kg, roulement sans glissement. Trajectoire centre d'inertie. V pour Ec=16J. Énergie de liaison par nucléon de Be-10. Données : m_Be=10,0113u, m_p=938,3MeV/C², m_n=939,6MeV/C², 1u=931,5MeV/C²."""),
("SM",2005,"Chimie",3,3,"""BAC SM/SE 2005 — Chimie — Coeff 3 — 3h
(Sujet non disponible au moment de la collecte — server error)"""),
("SM",2005,"Anglais",2,2,"""BAC SM/SE 2005 — Anglais — Coeff 2 — 2h
La Hyène et le Singe. Compléter (hungry/replied/branches/ago/story/upset/back/doing/she/goat/down). Compréhension.
Unless/Afraid/Until/As well as/As soon as : utiliser pour construire des phrases.
Associer colonnes A et B avec "as"."""),
("SM",2005,"Philosophie",2,2,"""BAC SM/SE 2005 — Philosophie — Coeff 2 — 2h
Rousseau : « Renoncer à sa liberté, c'est renoncer à sa qualité d'homme, aux droits de l'humanité même à ses devoirs. »"""),
("SM",2004,"Mathématiques",4,4,"""BAC SM 2004 — Mathématiques — Coeff 4 — 4h
A) Euclide : (x,y) tels que 45x-28y=1. Résoudre dans Z². Résoudre 45x-28y=6 dans Z².
B) f(x)=(x-1)e^(x+1). Limites. Asymptote axe des ordonnées en -∞. Variations. Courbe (C).
Aire du domaine limité par (C), axe des abscisses, x=-1 et x=1."""),
("SM",2004,"Physique",3,3,"""BAC SM 2004 — Physique — Coeff 3 — 3h
A-Théorie : Loi de Laplace. MRUV : espaces successifs en PA de raison a×θ².
B-Problème : Balle lancée verticalement vers le haut, h_max=20m. Vitesse initiale (théorème énergie cinétique). Équation horaire z(t). Temps de retour."""),
("SM",2004,"Chimie",3,3,"""BAC SM/SE 2004 — Chimie — Coeff 3 — 3h
A-Théorie : Équation bilan I⁻ + S₂O₈²⁻. Variation vitesse si T augmente ou [I⁻] diminue. KA pour HCOOH/HCOO⁻ et CH₃NH₃⁺/CH₃NH₂.
B-Pratique : Méthanoate de sodium (10⁻¹mol/L), pH=8,3. Espèces chimiques. Concentrations. Données : 10⁻⁸,³=5×10⁻⁹."""),
("SM",2004,"Anglais",2,2,"""BAC SM/SE 2004 — Anglais — Coeff 2 — 2h
Alec Slugg : compléter (then/a/drive/going/before/never/when/broke/felt/has). Conseils du docteur.
Tag questions : Mariama hasn't finished, You would like, Amadou ate, Lycee students, Don't drop.
Construire phrases avec before, as soon as, etc."""),
("SM",2003,"Mathématiques",4,4,"""BAC SM 2003 — Mathématiques — Coeff 4 — 4h
A) Dé cubique faces 6,6,6,5,4,3. Probabilité chaque face kx. Montrer k=1/30. Lancer 4 fois : P(2 fois le numéro 6).
B) g(x)=2x√x-3lnx+6 sur ]0;+∞[. Signe de g. f(x)=3lnx/x+x-1.
Limites en 0 et +∞. Variations via g. Asymptote oblique D:y=x-1. Position relative de (C) et (D). Construire (C) et (D)."""),
("SM",2003,"Physique",3,3,"""BAC SM 2003 — Physique — Coeff 3 — 3h
A-Théorie : Force de Lorentz : différence force électrostatique et magnétique. g=f(R,ρ) pour un astre.
B-Problème : Condensateur C=200nF, U₀=20V se décharge dans bobine L, R négligeable. Oscillations T₀=1,26ms. Calculer L. T₀ dépend de U₀ ?"""),
("SM",2003,"Chimie",3,3,"""BAC SM/SE 2003 — Chimie — Coeff 3 — 3h
A-Théorie : Dextrogyre/lévogyre. Représentation énantiomères acide amino-2 propénoïque. Alcool secondaire saturé d=2,52.
B-Pratique : 30cm³ CH₃COOH (10⁻²mol/L) + V cm³ NaOH (10⁻²mol/L) → pH=5,05. pKA=4,75. Volume NaOH. Concentrations des espèces."""),
("SM",2003,"Anglais",2,2,"""BAC SM/SE 2003 — Anglais — Coeff 2 — 2h
I. If clauses : Si elle avait un téléphone (appeler famille). Si j'avais une villa (bonne vie). Si tu étudiais bien (passer le bac). Si tu n'étais pas malade (aller danser). Si j'avais été bon footballeur (jouer au Real Madrid).
II. Questions correspondant aux réponses : Mont Loura, Université Conakry, Boké, lycée depuis 3 ans, Titanic 1912.
III. Paragraphe sur tes plans après l'école."""),
("SM",2003,"Économie",2,2,"""BAC SM 2003 — Économie — Coeff 2 — 2h
Les problèmes alimentaires sont particulièrement graves dans les pays du Sud.
Connaissant les réalités économiques de la Guinée, expliquez les causes liées à ce problème et proposez des solutions pour lutter contre ce fléau."""),
("SM",2002,"Mathématiques",4,4,"""BAC SM 2002 — Mathématiques — Coeff 4 — 4h
I) Losange ABCD, O centre, OB=2OA.
a) Ensemble M : (MA⃗+MB⃗-2MC⃗)·(2MB⃗-MC⃗+MD⃗)=0.
b) Ensemble M : MA²+MC²-2MD²=-6OA².
II) f(x)=ln|x²-1|. Sens de variation. Axe de symétrie. f(x)=2ln|x|+ln|1-1/x²|. Limite graphique.
III) U_n=∫[nπ;(n+1)π]e⁻ˣsinxdx. Calculer U_n par intégration par parties. Suite géométrique."""),
("SM",2002,"Physique",3,3,"""BAC SM 2002 — Physique — Coeff 3 — 3h
Rails l=25cm, R=0,5Ω (conducteur), r=0,5Ω (tige), B=1T perpendiculaire, v=10m/s.
1. Sens courant induit. 2. f.é.m. et intensité. 3. Force électromagnétique et caractéristiques. 4. Puissance nécessaire."""),
("SM",2002,"Chimie",3,3,"""BAC SM/SE 2002 — Chimie — Coeff 3 — 3h
Théorie : Produit ionique de l'eau. Isomère de conformation vs configuration. Alcools (définition + 2 exemples).
Pratique : Corps A de formule CnH₂nO. Oxydation complète de 1g → 2,45g CO₂. Trouver n. DNPH→précipité jaune. AgNO₃→dépôt argent. KMnO₄ en milieu acide → acide méthyl-2 propénoïque. Nature, formule, nom. Réaction d'oxydo-réduction."""),
("SM",2002,"Philosophie",2,2,"""BAC SM/SE 2002 — Philosophie — Coeff 2 — 2h
« Examinez la formule Faits + Langage = Science »"""),
("SM",2001,"Mathématiques",4,4,"""BAC SM 2001 — Mathématiques — Coeff 4 — 4h
A) 1. Équations différentielles : a) x²+y²-2x²y'=0 ; b) y''+2y'+5y=0, f(0)=1, f'(0)=-1.
2. tan²α=(1-cos2α)/(1+cos2α). Vérifier tan(π/8)=√2-1. En déduire tan(3π/8).
3. A(3;1), B(0;2). M tel que 2MA⃗+MB⃗=3(i⃗/lna)+3a·ln(1/a)j⃗.
B) f(x)=ln(x+√(x²+4)). Ensemble de définition. (f(x)+f(-x))/2=ln2. Étude et courbe. Centre de symétrie. f bijection de R sur R."""),
("SM",2001,"Chimie",3,3,"""BAC SM/SE 2001 — Chimie — Coeff 3 — 3h
I-Théorie : Dissociation de l'eau. Réaction instantanée vs lente. Caractère réducteur des aldéhydes.
II-Pratique : 5,4g alcool primaire aromatique + excès Na (P=1,013bar). Équation générale alcool+Na. Masse molaire → formule brute → formule développée → nom."""),
("SM",2001,"Anglais",2,2,"""BAC SM/SE 2001 — Anglais — Coeff 2 — 2h
I. Remplir lacunes (petite activité de vente de kérosène). Questions pour les réponses (école, coucher, mari ingénieur, dormait quand pluie, dansé).
III. Need/needs/needn't/have to dans les phrases."""),
("SM",2001,"Philosophie",2,2,"""BAC SM/SE 2001 — Philosophie — Coeff 2 — 2h
Gaston Bachelard : « Quel que soit le point de départ de l'activité scientifique, elle ne peut pleinement convaincre qu'en quittant le domaine de base. Si elle expérimente, il faut raisonner si elle raisonne, il faut expérimenter. Toute application est transcendante. »"""),
("SM",2000,"Mathématiques",4,4,"""BAC SM 2000 — Mathématiques — Coeff 4 — 4h
A) Résoudre log₂x-log₈(5-2x)=1. Résoudre cos2x-√3sin2x+1=0.
Z₁=(√6-i√2)/2, Z₂=1-i. Module et argument de Z₁/Z₂. Calculer cos(π/12) et sin(π/12).
B) Plan euclidien P, repère orthonormé. φ : isométrie affine (contenu partiel en images).
f_a(x)=(a+2)x/(x+2-a). (C_a) globalement invariante par φ. Toutes les courbes passent par 2 points fixes."""),
("SM",2000,"Chimie",3,3,"""BAC SM/SE 2000 — Chimie — Coeff 3 — 3h
Théorie : Critère de choix d'un indicateur coloré. Métaux oxydables par HCl. Zinc + HCl.
Pratique : Ca(OH)₂ : 0,5g dans 500ml. Équation de dissociation. Concentration. [OH⁻] et pH.
Mélange A (Ca(OH)₂) + 500ml NaOH (pH inconnu). pH(C)=12,2. Déduire pH inconnu."""),
("SM",2000,"Économie",2,2,"""BAC SM 2000 — Économie — Coeff 2 — 2h
Après avoir expliqué les processus de transfert de la technique et de la technologie, dites leurs différentes formes. Dégagez ensuite les conséquences sur le développement socio-économique des pays du tiers monde."""),
("SM",2000,"Philosophie",2,2,"""BAC SM/SE 2000 — Philosophie — Coeff 2 — 2h
Anaxagore de Clazomènes : « L'Homme pense parce qu'il a des mains. » Après avoir expliqué cette pensée, vous montrerez que la pensée de l'Homme reste liée à son action."""),


# ══════════════════════════════════════════════════════════════════════════════
#  BAC SE 2016 → 2013 — sujets uniques (Bio-Géo, Maths SE, Physique SE)
# ══════════════════════════════════════════════════════════════════════════════
("SE",2016,"Biologie-Géologie",4,4,"""BAC SE 2016 — Biologie-Géologie — Coeff 4 — 4h
A-Géologie (5pts) :
1) Séisme enregistré, épicentre à 15000km. Définitions : séisme/séismographe/séismogramme/épicentre.
Vitesse ondes P (18min après déclenchement), S (12min après P), L (14min après P). Conclusion.
2) Trilobites/nummulites/ammonites → fossiles caractéristiques. Définition. Ère ou période de chacun.
3) Origine oxygène atmosphérique. Conséquences de son apparition sur l'évolution de la vie.
B-Biologie (15pts) :
I. Cellule musculaire et reconstitution d'ATP. Exposé clair, synthétique, illustré.
II. Quantité d'ADN par cellule d'oignon (racine) : t=[0;1;1h45;1h50;3;5h30;7;9;10;12;13h45;13h50;15]h,
quantités : [8;8;8;4;4;4;5;7;8;8;8;4;4]. Tracer courbe variation ADN."""),
("SE",2016,"Mathématiques",3,3,"""BAC SE 2016 — Mathématiques — Coeff 3 — 3h
Exercice 1 (5pts) : Dés cubiques : rouge (6;6;6;5;5;4), noir (3;3;3;2;2;1). Simultanément, X=r-n.
a) Loi de probabilité de X. b) Espérance mathématique et variance.
Exercice 2 (3pts) : Système dans C×C : (1+i)z-iz'=2+i et (2+i)z+(2-i)z'=7-4i.
Problème (12pts) : f(x)=(1/2)ln((1+x)/(1-x)) sur ]-1;1[. Courbe (C), unité 2cm.
1. Limites en -1 et +1. Interprétation graphique.
2a. Montrer f'(x)=1/(1-x²). 2b. Tableau de variation. 2c. Tangente (T) au point d'abscisse 0.
3. g(x)=f(x)-x. Sens de variation. g(0). Signe de g. Position de (C) par rapport à (T). Tracer (C) et (T)."""),
("SE",2016,"Physique",3,3,"""BAC SE 2016 — Physique — Coeff 3 — 3h
A-Théorie : Phénomène de diffraction de la lumière.
B-Pratique :
I. Dosage volumique sanguin via Na-24 (Z=11, A=23). Formation Na-24 par bombardement neutrons.
Désintégration Na-24 (T=15h). Injection 10cm³, C=10⁻³mol/L. Quantité initiale. Quantité après 7h30min.
Prélèvement 10cm³ : 1,4×10⁻⁸mol Na-24. Volume sanguin de l'individu.
II. Mobile a=4,1m/s², x(0)=1m, V(0)=-3m/s. Nature du mouvement. V(t) et x(t).
Dates de passage par O. Vitesses correspondantes. Changement de sens ? date et position.
III. Circuit RLC série : bande passante=100Hz, f_résonance=700Hz. Facteur de qualité.
U_eff=5V. Tension aux bornes du condensateur à la résonance."""),
("SE",2015,"Biologie-Géologie",4,4,"""BAC SE 2015 — Biologie-Géologie — Coeff 4 — 4h
A-Géologie (5pts) :
1) Lithosphère et asthénosphère : nature pétrographique.
2) Formes et traces d'activités biologiques des êtres disparus. Intérêt des fossiles.
3) Réseau GEOSCOPE, séisme Hokkaïdo 28/09/2004. Dispositif géophysique. Noms des enregistrements. Différentes ondes, ordre d'arrivée. Station CAN (Canberra, 8658km) : onde PKIKP, 11min56s. Type d'onde, trajet, nature couches traversées.
B-Biologie (15pts) :
1. Cœur de chien isolé (120bat/min vs 90 en place). Ablation nœud sinusal → contractions simultanées OA+V, 80bat/min.
Interprétation. Après section faisceau de His : OA=120bat/min, V=60bat/min.
2. Structures appareils génitaux (tableau homme/femme : organes producteurs, conduits, glandes annexes). Étapes fécondation.
3. Couple cobayes gris lisses → 128 petits : 78 gris lisses, 19 gris rudes, 31 blancs (26 lisses, 5 rudes). Génotypes possibles gris lisses. Génotype couple acheté. Lignée pure blancs rudes. Lignée pure gris rudes."""),
("SE",2015,"Mathématiques",3,3,"""BAC SE 2015 — Mathématiques — Coeff 3 — 3h
Exercice 1 (4pts) : Suite u_n : u₀=0, u_{n+1}=(2u_n+3)/(u_n+4). v_n=(u_n-1)/(u_n+3) → géométrique. Raison. v_n puis u_n.
Exercice 2 (7pts) : u=√(2-√2)-i√(2+√2). Calculer u² et u⁴. Module et argument de u⁴. Déduire module et arg de u. Ensemble M : |u×z|=8.
Problème (9pts) : f(x)=ln(eˣ+e⁻ˣ) sur [0;+∞[.
Limite en +∞. Montrer f(x)=x+ln(1+e⁻²ˣ). Asymptote D:y=x. Position relative.
Sens de variations. Tableau de variation. Tracer (D) et (C)."""),
("SE",2015,"Physique",3,3,"""BAC SE 2015 — Physique — Coeff 3 — 3h
A-Théorie : Satellite géostationnaire. Conservation énergie mécanique. Radioactivité.
B-Pratique :
I. x=t²-4t+3 (t≥0). Vitesse et accélération. Date annulation vitesse et abscisse de M. Intervalles accéléré/retardé. Date M à x=0.
II. Rb-87 → Sr-87. Équation (type radioactivité). Activité de 1g de Rb-87, T=47×10⁹ans. M_Rb=87g/mol, N_A=6,02×10²³mol⁻¹."""),
("SE",2014,"Biologie-Géologie",4,4,"""BAC SE 2014 — Biologie-Géologie — Coeff 4 — 4h
A-Géologie (5pts) :
1) Séisme, volcanisme, orogénèse → mobilité lithosphère. Définition lithosphère. Caractéristiques lithosphère continentale. Mouvements de plaques aboutissant à chaque phénomène.
2) Définir : coulissage, australopithecus, hydrosphère.
3) Trilobites/bélemnites/nummulites/ammonites → fossiles. Associer ère ou période.
4) Classer en ordre : Soleil, ozone, nébuleuse, terre, vie, hydrosphère, lithosphère, vie terrestre, atmosphère primitive.
B-Biologie (15pts) :
I. Neurone = unité histologique du système nerveux. Schéma.
II. Structures A (réponse graduée) et B (réponse tout-ou-rien) à stimulations 0→9 u.a.
A : 0;0;110;180;310;410;460;600;680;680V. B : 0;0;0;180;180;180;180;180;180;180V.
Courbes, analyse, identification, lois.
III. Tomates : petit fruit [P] dominant gros [g], codominance N/0 pour maturation. Indépendance des gènes.
Lignée pure petits+pas maturation × lignée pure gros+maturation normale.
F1, F2. Proportion phénotype recherché (gros à maturation ralentie). Phénotypes nouveaux."""),
("SE",2014,"Mathématiques",3,3,"""BAC SE 2014 — Mathématiques — Coeff 3 — 3h
Partie A (4pts) : u=(ai-4b)/(5+3i), a,b∈R*.
1. Déterminer a et b si |u|=1 et arg(u)=3π/4. 
2a. a=b=√2 : calculer u¹²+u¹⁶. 2b. Montrer u^(4m)+u^(4n)=0 pour m pair et n impair.
Partie B (12pts) : f(x)=2e^(2x)/(e^(2x)-1). Courbe (C), unité 2cm.
1. Ensemble Df. Limites aux bornes.
2. Variations de f.
3. Montrer I(0;1) est centre de symétrie.
4. Construire (C). Asymptotes. Point A d'ordonnée 4.
5. Restriction g sur ]0;+∞[. Réciproque g⁻¹.
Partie C (4pts) : Bassin 30 poissons (5 carpes, 10 tanches, 15 gardons). Filet de 4.
P(tous gardons), P(aucun gardon), P(au moins 1 gardon), P(1 carpe+1 tanche+2 gardons), P(≥2 carpes)."""),
("SE",2014,"Physique",3,3,"""BAC SE 2014 — Physique — Coeff 3 — 3h
A-Théorie : Loi de Faraday-Lenz. 4ème loi de Newton. 3ème loi de Kepler.
B-Pratique :
1. Interférences : ordre 6 en M, λ=589nm. Différence de marche. Minima avec lumière blanche (400-750nm).
2. Canon α=45°, objectif atteint après t=38,1s. V₀. Distance à l'objectif. g=9,8m/s².
3. Réacteur sous-marin : U-235. Composition nucléides U-234 et U-235.
U-235+n → Sr-94+Xe-140+2n. Masse U consommé en 30j, puissance 25MW.
Données : m(U-235)=234,9942u, m(Sr-94)=93,91541u, m(Xe-140)=139,9252u, m_n=1,009u, 1u=931,5MeV/C²."""),
("SE",2013,"Biologie-Géologie",4,4,"""BAC SE 2013 — Biologie-Géologie — Coeff 4 — 4h
A-Biologie :
I. Enregistrements A,B,C,D (muscle gastrocnémien grenouille + nerf sciatique). Description de A. Identification et analyse de B,C,D.
II. Séquence ADN : GTGCAGGATG. Structure double hélice. ARNm correspondant. Polypeptide.
Codes : UAC=Tyr, GAC=Asp, CUC=Leu, UCC=Ser, ACG=Thr.
III. Ménopause : progestérone et œstrogènes traces, FSH et LH très élevées. Interprétation. Schéma simplifié.
B-Géologie :
1) Sédiments jurassiques d'Europe : récifs coralliens. Situer le Jurassique. Type de fossile. Climat européen.
2) Causes et conséquences des déplacements des plaques lithosphériques."""),
("SE",2013,"Mathématiques",3,3,"""BAC SE 2013 — Mathématiques — Coeff 3 — 3h
(Contenu en images base64 dans l'original — sujet complet disponible sur exam224.com/sujets/show/bac-se-mathematiques-2013)
Problème sur nombres complexes Z et U. Barycentres. Fonctions réelles."""),
("SE",2013,"Physique",3,3,"""BAC SE 2013 — Physique — Coeff 3 — 3h
A-Théorie : Théorème de l'énergie cinétique. Effet photoélectrique et applications.
B-Pratique :
1. Plan incliné. a) α=30°, v=3,6km/h constante → force de frottement f. b) β=45° avec même f → accélération.
2. Bobine (R,L) : U continu=20V, I=2,5A. Puis u=18√2cos(100πt), I_eff=2A. Calculer L et R.
3. Désintégration Ra→Rn+α. Énergie en Joules et MeV. m_Ra=226,0960u, m_Rn=222,0869u, m_He=4,0026u, 1u=931,5MeV/C²."""),


# ══════════════════════════════════════════════════════════════════════════════
#  BAC SE 2012 → 2002 — 19 sujets uniques (Maths SE, Physique SE, Bio-Géo)
# ══════════════════════════════════════════════════════════════════════════════
("SE",2012,"Mathématiques",3,3,"""BAC SE 2012 — Mathématiques — Coeff 3 — 3h
A. U=cosθ+i·sinθ, V=cosθ-i·sinθ.
1. Montrer U×V=1. Calculer U+V, U-V, U^m+V^m, U^m-V^m (m∈Z).
2. Développer (U+V)³ et (U-V)³. Exprimer cos³θ et sin³θ linéairement.
3. Calculer I=∫₀^(π/3) cos³θ dθ et J=∫₀^(π/3) sin³θ dθ.
B. f(x)=e²ˣ/(eˣ-1), courbe (C).
1. Ensemble de définition. Limites aux bornes.
2. Montrer (Γ) : y=1+eˣ est asymptote à (C) en +∞. Position relative.
3. Variations de f. Tracer (Γ) et (C).
C. Résoudre dans R : log₃x=1/2+log₉(4x+15)."""),
("SE",2012,"Physique",3,3,"""BAC SE 2012 — Physique — Coeff 3 — 3h
A-Théorie : Définir : radioactivité, interfrange, potentiel d'arrêt. Lois de Kepler. Impesanteur.
B-Pratique :
I. Young : 10 interfranges avec λ=589nm → d₀=17,7mm ; avec λ inconnue → d₁=13,1mm. Calculer λ inconnue. Domaine spectral.
II. Proton m_p=1,67×10⁻²⁷kg, q=1,6×10⁻¹⁹C. Arrivée en A avec E_c=2eV (⊥ grille).
Grilles A et B parallèles, d=2cm, U_AB=1000V.
1. Vitesse en A. 2. Champ électrique entre A et B. 3. E_c et vitesse en B. 4. Durée du parcours AB."""),
("SE",2011,"Mathématiques",3,3,"""BAC SE 2011 — Mathématiques — Coeff 3 — 3h
A. 1) E={1;2;3;4}, F={a;b;c;d}. Nombre de bijections différentes de E sur F.
2) 4 hommes + 4 épouses. Partenaires tirés au sort (sexe différent, tout le monde danse).
P(chacun avec son épouse). P(2 hommes seulement avec leurs épouses). P(1 seul homme avec son épouse). En déduire P(aucun avec son épouse).
B. f définie sur un intervalle (contenu en images base64 dans l'original) : suite récurrente et étude de fonction."""),
("SE",2011,"Physique",3,3,"""BAC SE 2011 — Physique — Coeff 3 — 3h
A-Théorie : Lois de conservation dans une désintégration nucléaire. Interférences des ondes. Théorème du centre d'inertie. Expérience mettant en évidence le caractère ondulatoire de la lumière (schéma, conditions).
B-Pratique :
I. Cadre carré de courant continu dans champ magnétique uniforme. Plan du cadre ∥ lignes de champ, côtés à 45°. Représenter forces de Laplace. Comparer leurs valeurs.
II. Mouvement circulaire uniforme : v=14m/s, r=2m.
a) Vitesse angulaire. b) Fréquence.
III. U-235 + n → U-236. Calculer Δm. Énergie Q (J et MeV). m(U-235)=234,99332u, m(U-236)=235,99496u."""),
("SE",2010,"Biologie-Géologie",4,4,"""BAC SE 2010 — Biologie-Géologie — Coeff 4 — 4h
A-Biologie :
I. Rhodopsine : après exposition 2min à lumière vive → obscurité. Tableau % rhodopsine :
t(min) : 0;1;2;5;7;10;19 — % : 5;15;30;50;70;85;95.
Tracer courbe. Interpréter. Conséquences d'un régime carencé en vitamine A (court et long terme).
II. Circulation sanguine : schéma légendé. Structures et rôles des différents types de vaisseaux sanguins.
III. Caractère héréditaire lié au sexe. 2 exemples. Descendance probable pour : mari seul présente le caractère ; femme seule présente le caractère."""),
("SE",2010,"Mathématiques",3,3,"""BAC SE 2010 — Mathématiques — Coeff 3 — 3h
(Contenu partiellement en images base64 dans l'original)
A. Suite définie par récurrence. B. Problème de fonction réelle.
Mots-clefs : suite géométrique, limite, étude de f, variations, asymptote, tangente, tracer la courbe."""),
("SE",2010,"Physique",3,3,"""BAC SE 2010 — Physique — Coeff 3 — 3h
I. Cellule photoélectrique au césium. W₀=1,88eV, λ=0,496µm.
a) Effet photoélectrique possible ? Justifier. b) Énergie cinétique max et vitesse des électrons.
II. Pendule simple m=100g, T=1s, α=60°, s'arrête après 500 oscillations.
Puissance (W) d'un dispositif électrique pour entretenir ce mouvement.
III. Polonium-210 → He + Pb. Numéro atomique et masse de Pb. Énergie libérée (J et eV).
m_Po=210,05u, m_α=4,00u, m_Pb=206,04u, 1u=931,5MeV/C², 1MeV=1,6×10⁻¹³J.
IV. i=8,5cos(200πt) mA dans RLC série. Fréquence et valeur efficace.
R=100Ω, L=150mH, C=50µF. Impédance Z. Tension efficace aux bornes."""),
("SE",2009,"Mathématiques",3,3,"""BAC SE 2009 — Mathématiques — Coeff 3 — 3h
A. Z²=4√3+4i. Module et argument de Z².
Résoudre (E) dans C : a) forme algébrique (√3+1)²=4+2√3 ; b) forme trigonométrique.
En déduire cos(π/12) et sin(π/12).
B. f(x)=x+1+2e⁻ˣ sur R, courbe (C).
1. Étudier f. 2. Asymptote oblique à (C). 3. Tangentes T₁ et T₂ en x=-1 et x=0. Tracer T₁, T₂, (C).
C. Système dans R² : ln(xy)=5 et (ln x · ln y)²=36."""),
("SE",2009,"Physique",3,3,"""BAC SE 2009 — Physique — Coeff 3 — 3h
I. RC série sous 220V/50Hz. Ampèremètre : 4A. Voltmètre aux bornes de R : 96V.
a) Impédance et résistance R. b) Capacité C et tension à ses bornes. c) Facteur de puissance et puissance moyenne.
II. Voyageur en retard : v=5m/s, à 15m du train quand il démarre (a=10m/s²).
a) Équations horaires du voyageur et du wagon. b) Montrer que le voyageur ne peut rattraper le train. c) Distance minimale voyageur/wagon.
III. Young a=1mm, D=2m, λ=0,7µm. a) Interfrange. Nature frange centrale. b) Fréquence de la radiation.
IV. Bismuth-212 → α. Équation désintégration. Énergie en MeV. m_α=4,0015u, m_Bi=211,9457u, m_Tl=207,9375u, 1u=931,5MeV/c²."""),
("SE",2008,"Mathématiques",3,3,"""BAC SE 2008 — Mathématiques — Coeff 3 — 3h
A. 5 témoins, 2 menteurs inconnus. On questionne 2 témoins au hasard (indépendamment).
P(2 versions véridiques). P(2 versions contradictoires). P(2 versions fausses).
B. f définie sur R (contenu partiellement en images base64). Étude de f. Variations. Tangente. Tracer la courbe."""),
("SE",2008,"Physique",3,3,"""BAC SE 2008 — Physique — Coeff 3 — 3h
A-Théorie : Rayonnements radioactifs : composition, caractéristiques et propriétés.
B-Pratique :
I. Projectile V₀=30m/s, α=50°. Équation de trajectoire. Flèche. Angle pour flèche maximale et hauteur atteinte. Énergie cinétique au point culminant.
II. Polonium-210 : N=N₀e^(-0,005t) (t en jours). Demi-vie T. Fractions restantes à 2T et 3T. Graphe N=f(t).
III. Générateur f=200Hz. Impédances de :
a) R=23Ω b) C=80µF c) Bobine L=34mH (résistance négligeable)."""),
("SE",2007,"Mathématiques",3,3,"""BAC SE 2007 — Mathématiques — Coeff 3 — 3h
A. Plan complexe, repère (o;i;j), unité 1cm. Suite (M_n) d'affixes (z_n) : z₀=8, z_{n+1}=... (contenu en images base64).
Suite géométrique. Tracer les premiers points. Spirale logarithmique.
B. Étude de f (contenu en images base64). Variations. Asymptote. Tangente. Construire (C)."""),
("SE",2007,"Physique",3,3,"""BAC SE 2007 — Physique — Coeff 3 — 3h
I. Rails conducteurs l, tige MN perpendiculaire, résistance R constante, champ B vertical (vers le haut). MN se déplace à vitesse constante v.
f.é.m. induite dans MN (caractéristiques). Intensité et sens du courant induit. Force électromagnétique sur MN. Puissance mécanique nécessaire pour v=constante.
Données : L=20cm, R=20Ω, B=0,5T, V=5m/s.
II. Cellule photoélectrique λ₀=0,50µm (seuil).
1. Vitesse max et potentiel d'arrêt des électrons.
2. Avec λ₀=0,50µm et tension cathode U=75V → E_c max des électrons à l'anode.
h=6,62×10⁻³⁴J·s, C=3×10⁸m/s, m_e=9,1×10⁻³¹kg."""),
("SE",2006,"Mathématiques",3,3,"""BAC SE 2006 — Mathématiques — Coeff 3 — 3h
A. 1) Résoudre dans C : 4Z²+8Z+29=0. 2) Représenter A, B (solutions) et C(2-3/2·i). Montrer ABC isocèle.
B. f(x)=eˣ/x³ sur R*. Courbe (C).
1. Étudier les variations de f.
2a. Tangente (T) à (C) en x=1. 2b. Tracer (T) puis (C).
c. Calculer I=∫₀ˣ sin(t)cos⁵(t)dt et J=∫₀ˣ sin(t)cos³(t)dt."""),
("SE",2005,"Mathématiques",3,3,"""BAC SE 2005 — Mathématiques — Coeff 3 — 3h
A. Z=(1+√2-i)/(1+√2+i).
1a. Forme algébrique. b. Module et argument.
2. Calculer Z̄⁶, Z̄⁸, Z̄²⁰⁰⁵ sous forme algébrique.
B. Linéariser sin²x·cos⁴x.
C. f(x)=1/(x·lnx).
1. Variations de f. Courbe (C) dans repère (o;i;j).
2. Aire du domaine : e≤x≤e², e≤y≤f(x)."""),
("SE",2005,"Physique",3,3,"""BAC SE 2005 — Physique — Coeff 3 — 3h
I. Condensateur C=100µF (chargé) + bobine L=0,1H (R négligeable).
a) Pulsation ω₀ des oscillations. b) Période propre T₀. Fréquence propre N₀.
II. Bille m, V₀=12m/s, α=30°. Équations horaires des coordonnées. Équation de la trajectoire. Portée et flèche.
III. u=15cos(200πt) V aux bornes d'une bobine L=150mH (non résistive).
a) Fréquence. b) Intensité efficace. c) Intensité instantanée.
IV. Ascenseur m=800kg, d=7m en t=3s (MRUV). Tension T du câble. g=9,8m/s²."""),
("SE",2004,"Physique",3,3,"""BAC SE 2004 — Physique — Coeff 3 — 3h
Solénoïde d'axe horizontal : 100 spires, Ø=8cm, I=10A. Mobile autour d'un axe vertical.
Champ B=5×10⁻²T produit brusquement, lignes d'induction ∥ axe solénoïde mais de sens contraire.
1. Position finale du solénoïde.
2. Travail effectué par les forces électromagnétiques au cours de la rotation."""),
("SE",2003,"Physique",3,3,"""BAC SE 2003 — Physique — Coeff 3 — 3h
Photon λ=3,0×10⁻¹²m diffusé par un électron libre au repos, dans une direction θ=60° avec la direction initiale.
1. Longueur d'onde λ' du photon diffusé.
2. Énergie cinétique acquise par l'électron. Module V de sa vitesse."""),
("SE",2002,"Physique",3,3,"""BAC SE 2002 — Physique — Coeff 3 — 3h
1. Corps de masse m en orbite circulaire de rayon R autour d'un astre de masse M à vitesse constante. Relation entre période T et rayon R.
2. Application numérique : Terre autour du Soleil (R=150×10⁶km, T=365j). Lune autour de la Terre (R=38×10⁴km, T=28j). Masse du Soleil. M_Terre=6×10²⁴kg."""),

]


class Command(BaseCommand):
    help = "Charge les sujets BAC Guinée — données statiques copiées depuis exam224.com"

    def handle(self, *args, **options):
        created = updated = 0
        with transaction.atomic():
            for row in BAC_DATA:
                series, year, subject_name, coef, duree_h, content = row
                content = content.strip()
                if not content:
                    continue

                try:
                    from learning.models import Document, Subject
                except ImportError:
                    from content.models import Document, Subject

                subject_obj, _ = Subject.objects.get_or_create(
                    name=subject_name,
                    defaults={'icon': ICONS.get(subject_name, '📚')}
                )

                title = f"BAC {series} {year} — {subject_name}"
                desc  = f"Sujet officiel BAC {series} Guinée, session {year}. {subject_name} — Coeff. {coef} — Durée {duree_h}h."
                slug  = (subject_name.lower()
                         .replace('é','e').replace('è','e').replace('ê','e')
                         .replace('â','a').replace('ô','o').replace(' ','-')
                         .replace('/','').replace('--','-'))

                doc, is_new = Document.objects.update_or_create(
                    title=title,
                    defaults={
                        'description':  desc,
                        'doc_type':     'COURS',
                        'subject':      subject_obj,
                        'level':        'Terminale',
                        'is_free':      True,
                        'content':      content,
                        'external_url': f"https://exam224.com/sujets/show/bac-{series.lower()}-{slug}-{year}",
                    }
                )
                if is_new: created += 1
                else:      updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {created+updated} sujets chargés — {created} créés, {updated} mis à jour"
        ))
