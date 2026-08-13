from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Crée ou met à jour le superadmin Kharandi"

    def handle(self, *args, **kwargs):
        from users.models import User, Profile
        from django.conf import settings

        phone    = getattr(settings, "ADMIN_PHONE", "").strip()
        password = getattr(settings, "ADMIN_PASSWORD", "").strip()
        if not phone or not password:
            raise CommandError("ADMIN_PHONE et ADMIN_PASSWORD doivent être définis.")

        user, created = User.objects.get_or_create(phone=phone)

        user.set_password(password)

        # ✅ Toujours forcer ADMIN même si le compte existait déjà
        user.role         = "ADMIN"
        user.is_staff     = True
        user.is_superuser = True
        user.is_active    = True
        user.save()

        # ✅ Profil avec onboarding terminé
        profile, _ = Profile.objects.get_or_create(user=user)
        if not profile.onboarding_completed:
            profile.onboarding_completed = True
            profile.save(update_fields=["onboarding_completed"])

        action = "créé" if created else "mis à jour (rôle ADMIN forcé)"
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ Superadmin '{phone}' — {action}"
        ))
