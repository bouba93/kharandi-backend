import io
import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from core.permissions import IsAdmin
from core.utils import API_EXCEPTIONS, error_response, internal_error_response

logger = logging.getLogger(__name__)

class TransactionsPDFView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from payments.models import Transaction
        from payments.serializers import TransactionSerializer
        txs  = Transaction.objects.filter(user=request.user) if request.user.role != "ADMIN" else Transaction.objects.select_related("user").all()
        data = TransactionSerializer(txs, many=True).data
        html = f"<html><body><h1>Transactions Kharandi</h1><p>{len(data)} transaction(s)</p></body></html>"
        try:
            from weasyprint import HTML
            resp = HttpResponse(HTML(string=html).write_pdf(), content_type="application/pdf")
            resp["Content-Disposition"] = 'attachment; filename="transactions.pdf"'
            return resp
        except API_EXCEPTIONS:
            raise
        except Exception:
            # 503 : la génération PDF dépend de WeasyPrint et de ses bibliothèques
            # système. Une indisponibilité est temporaire, pas une requête invalide.
            return internal_error_response(
                logger,
                "export PDF des transactions",
                message="Export PDF momentanément indisponible.",
                status=503,
            )

class StudentReportPDFView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        from learning.models import QCM
        qcms = QCM.objects.filter(user=request.user, completed=True)
        avg  = sum(q.score for q in qcms if q.score)/qcms.count() if qcms.count() else 0
        html = f"<html><body><h1>Bulletin {request.user.phone}</h1><p>Moyenne : {round(avg,2)}/20</p></body></html>"
        try:
            from weasyprint import HTML
            resp = HttpResponse(HTML(string=html).write_pdf(), content_type="application/pdf")
            resp["Content-Disposition"] = 'attachment; filename="bulletin.pdf"'
            return resp
        except API_EXCEPTIONS:
            raise
        except Exception:
            return internal_error_response(
                logger,
                "export PDF du bulletin",
                message="Export PDF momentanément indisponible.",
                status=503,
            )

class StatsExcelView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        import io, openpyxl
        from users.models import User
        from payments.models import Transaction
        wb = openpyxl.Workbook()
        ws = wb.active; ws.title = "Utilisateurs"
        ws.append(["ID","Téléphone","Rôle","Date"])
        for u in User.objects.all(): ws.append([str(u.id), u.phone, u.role, str(u.date_joined)[:19]])
        ws2 = wb.create_sheet("Transactions"); ws2.append(["Référence","Montant","Devise","Statut","Date"])
        for tx in Transaction.objects.all(): ws2.append([tx.reference, float(tx.amount), tx.currency, tx.status, str(tx.created_at)[:19]])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = 'attachment; filename="stats.xlsx"'
        return resp
