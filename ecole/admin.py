from django.contrib import admin
from .models import School, SchoolTeacher, SchoolStudent, SchoolGrade, SchoolPayment, SchoolAbsence, SchoolClass

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "code", "is_activated", "subscription_active"]
    list_filter  = ["is_activated", "subscription_active"]
    search_fields= ["name", "email", "code"]

@admin.register(SchoolTeacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "school"]

@admin.register(SchoolStudent)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["name", "matricule", "school", "school_class"]
    search_fields= ["name", "matricule"]

admin.site.register(SchoolGrade)
admin.site.register(SchoolPayment)
admin.site.register(SchoolAbsence)
admin.site.register(SchoolClass)
