from django.contrib import admin

from .models import GuineaKnowledgeEntry


@admin.register(GuineaKnowledgeEntry)
class GuineaKnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "priority", "verified_on", "is_active", "updated_at",
    )
    list_filter = ("category", "is_active", "verified_on")
    search_fields = ("title", "content", "keywords", "source_title")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-priority", "title")
