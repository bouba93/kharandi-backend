from django.contrib import admin
from .models import (News, SchoolRanking, StudyAbroad, Scholarship,
                     TutorAd, Notification, ReadingProgress)


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display  = ("university", "program_name", "country", "level", "is_active", "created_at")
    list_filter   = ("is_active", "country", "level")
    search_fields = ("university", "program_name", "country", "excerpt")


@admin.register(SchoolRanking)
class SchoolRankingAdmin(admin.ModelAdmin):
    list_display  = ("rank", "name", "location", "school_type", "score", "year")
    list_filter   = ("year", "school_type")
    search_fields = ("name", "location")


@admin.register(StudyAbroad)
class StudyAbroadAdmin(admin.ModelAdmin):
    list_display  = ("university", "program_name", "country", "level", "is_active")
    list_filter   = ("is_active", "country")
    search_fields = ("university", "program_name")


for model in (News, TutorAd, Notification, ReadingProgress):
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
