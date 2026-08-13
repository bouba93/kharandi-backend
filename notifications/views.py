from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from core.permissions import IsAdmin
from core.utils import success_response, error_response
from .tasks import send_sms, send_welcome_sms

class SendWelcomeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        send_welcome_sms(str(request.user.id))
        return success_response(message="SMS de bienvenue envoyé.")

class SendCustomView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        phones  = request.data.get("phones", [])
        message = request.data.get("message", "").strip()
        if not phones or not message:
            return error_response("phones et message sont obligatoires.")
        sent = sum(1 for p in phones if send_sms(p, message))
        return success_response(message=f"{sent}/{len(phones)} SMS envoyé(s).")
