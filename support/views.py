from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from core.permissions import IsAdmin
from core.utils import success_response, error_response
from .models import Ticket, TicketReply
from .serializers import TicketSerializer, TicketCreateSerializer

class TicketListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = Ticket.objects.prefetch_related("replies").all() if IsAdmin().has_permission(request, self) \
             else Ticket.objects.filter(user=request.user).prefetch_related("replies")
        if s := request.query_params.get("status"): qs = qs.filter(status=s)
        return success_response(data=TicketSerializer(qs, many=True).data)
    def post(self, request):
        s = TicketCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ticket = s.save(user=request.user)
        return success_response(data=TicketSerializer(ticket).data, message="Ticket créé.", status=201)

class TicketDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def _get(self, pk, user):
        try: return Ticket.objects.get(id=pk) if user.role=="ADMIN" else Ticket.objects.get(id=pk, user=user)
        except Ticket.DoesNotExist: return None
    def get(self, request, pk):
        t = self._get(pk, request.user)
        if not t: return error_response("Ticket introuvable.", status=404)
        return success_response(data=TicketSerializer(t).data)
    def patch(self, request, pk):
        t = self._get(pk, request.user)
        if not t: return error_response("Ticket introuvable.", status=404)
        if (ns := request.data.get("status")) and request.user.role == "ADMIN":
            t.status = ns; t.save(update_fields=["status"])
        if msg := request.data.get("message"):
            TicketReply.objects.create(ticket=t, author=request.user, message=msg,
                                       is_staff=(request.user.role=="ADMIN"))
        return success_response(data=TicketSerializer(t).data, message="Ticket mis à jour.")
