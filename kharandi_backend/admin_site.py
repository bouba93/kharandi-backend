from django.contrib.admin import AdminSite
from .admin_dashboard import dashboard_stats


class KharandiAdminSite(AdminSite):
    site_header = "Kharandi Administration"
    site_title = "Kharandi Admin"
    index_title = "Tableau de bord"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["dashboard_stats"] = dashboard_stats()
        return super().index(request, extra_context=extra_context)


kharandi_admin_site = KharandiAdminSite(name="kharandi_admin")
