"""
users/admin.py — Back-office des dossiers KYC répétiteurs
─────────────────────────────────────────────────────────
User, Profile et OTPRecord sont déjà enregistrés dans core/admin.py : on ne les
redéclare pas ici (Django lèverait AlreadyRegistered).

Ce module ajoute UNIQUEMENT :
  - `TutorKYCAdmin` : liste, filtres, recherche, examen, actions de masse ;
  - une vue de téléchargement sécurisée des pièces d'identité.

Les documents KYC ne sont JAMAIS rendus publics : la vue de téléchargement est
servie par Django, derrière la session admin, et vérifie la permission
`users.view_tutorkyc`. Aucun lien direct vers /media/ n'est produit.
"""
from django.contrib import admin, messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import ngettext

from .models import TutorKYC

CHAMPS_DOCUMENTS = ("document_front", "document_back", "selfie", "diploma_file")


@admin.register(TutorKYC)
class TutorKYCAdmin(admin.ModelAdmin):
    list_display = (
        "telephone_repetiteur", "full_name", "document_type", "statut_colore",
        "submitted_at", "reviewed_at", "reviewed_by",
    )
    list_filter = ("status", "document_type", "submitted_at")
    search_fields = (
        "user__phone", "full_name", "document_number",
        "user__profile__display_name", "user__profile__first_name",
        "user__profile__last_name",
    )
    date_hierarchy = "submitted_at"
    ordering = ("-submitted_at",)
    list_select_related = ("user", "reviewed_by")
    autocomplete_fields = ()
    raw_id_fields = ("user", "reviewed_by")
    actions = ("approuver_dossiers", "refuser_dossiers")

    fieldsets = (
        ("Répétiteur", {
            "fields": ("user", "full_name", "birth_date", "address",
                       "diploma", "experience_years"),
        }),
        ("Pièce d'identité", {
            "fields": ("document_type", "document_number", "liens_documents"),
        }),
        ("Décision", {
            "fields": ("status", "rejection_reason", "admin_notes",
                       "submitted_at", "reviewed_at", "reviewed_by"),
            "description": "Enregistrer avec le statut « Approuvé » ou « Refusé » "
                           "renseigne automatiquement l'examinateur et la date. "
                           "Un refus exige un motif.",
        }),
    )

    # ── Colonnes calculées ──────────────────────────────────────────────────
    @admin.display(description="Téléphone", ordering="user__phone")
    def telephone_repetiteur(self, obj):
        return obj.user.phone

    @admin.display(description="Statut", ordering="status")
    def statut_colore(self, obj):
        couleurs = {
            TutorKYC.Status.PENDING: "#b45309",
            TutorKYC.Status.APPROVED: "#15803d",
            TutorKYC.Status.REJECTED: "#b91c1c",
        }
        return format_html(
            '<b style="color:{}">{}</b>',
            couleurs.get(obj.status, "#334155"), obj.get_status_display(),
        )

    @admin.display(description="Documents (accès réservé)")
    def liens_documents(self, obj):
        if not obj.pk:
            return "—"
        libelles = {
            "document_front": "Recto",
            "document_back": "Verso",
            "selfie": "Selfie",
            "diploma_file": "Diplôme",
        }
        liens = []
        for champ in CHAMPS_DOCUMENTS:
            if getattr(obj, champ, None):
                url = reverse("admin:users_tutorkyc_document",
                              args=[obj.pk, champ])
                liens.append(format_html('<a href="{}" target="_blank">{}</a>',
                                         url, libelles[champ]))
        if not liens:
            return "Aucun document déposé."
        return format_html(" &nbsp;|&nbsp; ".join(["{}"] * len(liens)), *liens)

    # ── Protection d'un dossier déjà validé ─────────────────────────────────
    def get_readonly_fields(self, request, obj=None):
        base = ["submitted_at", "reviewed_at", "reviewed_by", "liens_documents"]
        if obj and obj.status == TutorKYC.Status.APPROVED:
            # Un dossier approuvé n'est pas modifiable par inadvertance :
            # les pièces et l'identité sont figées. Pour le rouvrir, passer par
            # un superutilisateur (voir ci-dessous).
            if not request.user.is_superuser:
                base += ["user", "full_name", "document_type", "document_number",
                         "birth_date", "address", "diploma", "experience_years",
                         "status", "rejection_reason"]
        return base

    def has_add_permission(self, request):
        # Un dossier KYC est déposé par le répétiteur via l'API, avec ses
        # propres pièces : le créer à la main dans l'admin n'a pas de sens et
        # produirait un dossier sans document.
        return False

    def has_delete_permission(self, request, obj=None):
        # Pièce de conformité : suppression réservée aux superutilisateurs.
        return bool(request.user.is_superuser)

    def save_model(self, request, obj, form, change):
        """Applique la décision via les méthodes métier du modèle.

        On ne duplique pas la logique : `approve()` / `reject()` restent la
        seule implémentation (même comportement depuis l'API, l'admin ou un
        script), y compris la synchronisation de `Profile.tutor_status`.
        """
        precedent = None
        if change and obj.pk:
            precedent = TutorKYC.objects.filter(pk=obj.pk).values_list(
                "status", flat=True).first()

        nouveau_statut = obj.status

        if precedent == TutorKYC.Status.APPROVED and nouveau_statut != TutorKYC.Status.APPROVED:
            if not request.user.is_superuser:
                messages.error(
                    request,
                    "Ce dossier est déjà approuvé : seul un superutilisateur "
                    "peut retirer sa validation. Aucune modification enregistrée.",
                )
                return

        if nouveau_statut == TutorKYC.Status.REJECTED and not (obj.rejection_reason or "").strip():
            messages.error(
                request,
                "Un refus doit comporter un motif : rien n'a été enregistré.",
            )
            return

        if nouveau_statut != precedent and nouveau_statut in (
            TutorKYC.Status.APPROVED, TutorKYC.Status.REJECTED
        ):
            obj.reviewed_by = request.user
            from django.utils import timezone
            obj.reviewed_at = timezone.now()

        super().save_model(request, obj, form, change)
        obj._synchroniser_profil()

    # ── Actions de masse ────────────────────────────────────────────────────
    @admin.action(description="Approuver les KYC sélectionnés")
    def approuver_dossiers(self, request, queryset):
        traites = ignores = 0
        for dossier in queryset.select_related("user"):
            if dossier.approve(par_admin=request.user):
                traites += 1
            else:
                ignores += 1
        if traites:
            self.message_user(request, ngettext(
                "%d dossier approuvé.", "%d dossiers approuvés.", traites,
            ) % traites, messages.SUCCESS)
        if ignores:
            self.message_user(
                request,
                f"{ignores} dossier(s) ignoré(s) : déjà approuvé(s).",
                messages.WARNING,
            )

    @admin.action(description="Refuser les KYC sélectionnés (motif à compléter)")
    def refuser_dossiers(self, request, queryset):
        motif_defaut = ("Dossier incomplet ou illisible. Merci de redéposer vos "
                        "pièces d'identité.")
        traites = ignores = 0
        for dossier in queryset.select_related("user"):
            if dossier.reject(motif=dossier.rejection_reason or motif_defaut,
                              par_admin=request.user):
                traites += 1
            else:
                ignores += 1
        if traites:
            self.message_user(request, ngettext(
                "%d dossier refusé.", "%d dossiers refusés.", traites,
            ) % traites, messages.WARNING)
        if ignores:
            self.message_user(
                request,
                f"{ignores} dossier(s) ignoré(s) : déjà approuvé(s), un refus "
                "doit alors être saisi dossier par dossier.",
                messages.WARNING,
            )

    # ── Téléchargement sécurisé des pièces ──────────────────────────────────
    def get_urls(self):
        perso = [
            path(
                "<uuid:pk>/document/<str:champ>/",
                self.admin_site.admin_view(self.telecharger_document),
                name="users_tutorkyc_document",
            ),
        ]
        return perso + super().get_urls()

    def telecharger_document(self, request, pk, champ):
        if champ not in CHAMPS_DOCUMENTS:
            raise Http404("Document inconnu.")
        if not request.user.has_perm("users.view_tutorkyc"):
            raise Http404("Accès refusé.")
        dossier = get_object_or_404(TutorKYC, pk=pk)
        fichier = getattr(dossier, champ, None)
        if not fichier:
            raise Http404("Aucun fichier pour ce champ.")
        reponse = FileResponse(fichier.open("rb"), as_attachment=False)
        # Aucun cache navigateur / proxy sur une pièce d'identité.
        reponse["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        reponse["X-Content-Type-Options"] = "nosniff"
        reponse["Content-Disposition"] = (
            f'inline; filename="kyc-{dossier.user.phone}-{champ}"'
        )
        return reponse


# ══════════════════════════════════════════════════════════════════════════════
#  Comptes Google liés — consultation seule
# ══════════════════════════════════════════════════════════════════════════════
#  L'administrateur voit QUI est lié à Google, avec quel email Google et depuis
#  quand. Rien d'autre : aucun client secret, aucun access token, aucun refresh
#  token n'est stocké par Kharandi, donc rien de tel ne peut être affiché.
#  La liaison ne se crée ni ne se modifie depuis l'admin : elle résulte du flux
#  OAuth vérifié. L'admin peut seulement la supprimer (retirer Google d'un
#  compte), ce qui ne touche ni le User, ni le Profile, ni les données métier.
# ══════════════════════════════════════════════════════════════════════════════
from .models import GoogleAccount  # noqa: E402


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = (
        "telephone_kharandi", "fournisseur", "email", "email_verified",
        "linked_at", "last_used_at",
    )
    list_filter = ("email_verified", "linked_at")
    search_fields = ("user__phone", "email", "google_sub")
    date_hierarchy = "linked_at"
    ordering = ("-linked_at",)
    list_select_related = ("user",)
    raw_id_fields = ("user",)

    readonly_fields = (
        "user", "fournisseur", "google_sub", "email", "email_verified",
        "given_name", "family_name", "linked_at", "last_used_at",
    )
    fieldsets = (
        ("Compte Kharandi", {"fields": ("user",)}),
        ("Compte Google", {
            "fields": ("fournisseur", "google_sub", "email", "email_verified",
                       "given_name", "family_name"),
            "description": "Informations transmises par Google et vérifiées par "
                           "le backend. Aucun jeton Google n'est conservé.",
        }),
        ("Suivi", {"fields": ("linked_at", "last_used_at")}),
    )

    @admin.display(description="Téléphone Kharandi", ordering="user__phone")
    def telephone_kharandi(self, obj):
        return obj.user.phone

    @admin.display(description="Fournisseur")
    def fournisseur(self, obj):
        return "Google"

    def has_add_permission(self, request):
        # Une liaison se crée uniquement par un flux OAuth vérifié.
        return False

    def has_change_permission(self, request, obj=None):
        return False
