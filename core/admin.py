from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from users.models import User, Profile, OTPRecord
from learning.models import Document, Subject, QCM
from payments.models import Plan, Subscription, Transaction
from ecommerce.models import Order, OrderItem
from support.models import Ticket, TicketReply

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ["phone", "role", "is_active", "is_staff", "date_joined"]
    list_filter   = ["role", "is_active"]
    search_fields = ["phone"]
    ordering      = ["-date_joined"]
    fieldsets     = (
        (None,          {"fields": ("phone", "role", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"fields": ("phone", "role", "password1", "password2")}),)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ["user", "first_name", "last_name", "school_level", "city", "onboarding_completed"]
    list_filter   = ["onboarding_completed"]
    search_fields = ["user__phone", "first_name", "last_name"]

@admin.register(OTPRecord)
class OTPAdmin(admin.ModelAdmin):
    list_display = ["phone", "verificationid", "verified", "sent_at", "expires_at"]
    list_filter  = ["verified"]

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "icon"]

def _flush_bac_cache(modeladmin, request, queryset):
    from core.redis_utils import bac_subjects_cache_clear
    from django.contrib import messages as django_messages
    bac_subjects_cache_clear()
    modeladmin.message_user(request, "✅ Cache sujets BAC vidé.", django_messages.SUCCESS)
_flush_bac_cache.short_description = "Vider le cache Redis des sujets BAC"

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display  = ["title", "doc_type", "subject", "level", "is_free", "downloads"]
    list_filter   = ["doc_type", "level", "is_free"]
    search_fields = ["title"]
    actions       = [_flush_bac_cache]
    fieldsets     = (
        ("Informations générales", {
            "fields": ("title", "description", "doc_type", "subject", "level", "is_free", "price", "has_certification")
        }),
        ("Contenu", {
            "description": "Remplissez UNE des 3 options : texte direct, fichier PDF/vidéo, ou URL externe",
            "fields": ("content", "file", "external_url", "thumbnail"),
        }),
    )

@admin.register(QCM)
class QCMAdmin(admin.ModelAdmin):
    list_display = ["user", "subject", "topic", "difficulty", "score", "completed"]
    list_filter  = ["difficulty", "completed"]

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "period", "price", "currency", "is_active"]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ["user", "plan", "status", "start_date", "end_date"]
    list_filter   = ["status"]
    search_fields = ["user__phone"]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display    = ["reference", "user", "amount", "currency", "status", "created_at"]
    list_filter     = ["status", "provider"]
    search_fields   = ["reference", "user__phone"]
    readonly_fields = ["webhook_payload"]

class OrderItemInline(admin.TabularInline):
    model = OrderItem; extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "total", "status", "created_at"]
    list_filter  = ["status"]
    inlines      = [OrderItemInline]

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display  = ["title", "user", "category", "status", "priority", "created_at"]
    list_filter   = ["status", "category"]
    search_fields = ["title", "user__phone"]



