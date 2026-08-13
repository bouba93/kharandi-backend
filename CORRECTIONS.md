# Backend Kharandi corrigé

Cette archive contient les corrections de stabilité et de sécurité appliquées au backend.

## Principales corrections

- démarrage Django et migrations remis en état ;
- connexion par mot de passe basée sur le hash Django, sans identifiants de secours ;
- création cohérente des profils élève, parent, répétiteur et vendeur ;
- protection contre l’auto-promotion administrateur et le crédit libre du wallet ;
- contrôle d’accès des écoles, enseignants et parents avec jetons signés et périmètre par école ;
- montants des commandes et abonnements recalculés côté serveur ;
- webhook LengoPay protégé par signature HMAC SHA-256 ;
- opérations de paiement et de points rendues atomiques ;
- calcul des scores QCM et conversion des points corrigés ;
- entrées Karamo validées, quotas remboursés en cas d’échec et solutions QCM masquées avant soumission ;
- images Karamo contrôlées et QCM strictement validés avant enregistrement ;
- base Karamo extensible de neuf fiches sourcées sur la Guinée, administrable dans Django ;
- recherche locale guinéenne combinée à la recherche web pour les informations récentes ;
- secrets et identifiants sensibles retirés de la documentation.

## Mise en route

1. Copier `.env.example` vers `.env` et renseigner les valeurs réelles.
2. Utiliser une longue `SECRET_KEY` et définir `LENGOPAY_WEBHOOK_SECRET`.
3. Installer les dépendances : `pip install -r requirements.txt`.
4. Appliquer les migrations : `python manage.py migrate`.
5. Créer ou mettre à jour l’administrateur : `python manage.py create_superadmin`.
6. Lancer les tests : `python manage.py test`.

Si une clé LengoPay ou Nimba a déjà été publiée dans l’historique Git, elle doit être révoquée et remplacée auprès du fournisseur avant la mise en production.
