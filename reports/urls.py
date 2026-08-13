from django.urls import path
from .views import TransactionsPDFView, StudentReportPDFView, StatsExcelView
urlpatterns = [
    path("transactions/pdf/", TransactionsPDFView.as_view(),  name="report-tx-pdf"),
    path("student/pdf/",      StudentReportPDFView.as_view(), name="report-student-pdf"),
    path("stats/excel/",      StatsExcelView.as_view(),        name="report-stats-excel"),
]
