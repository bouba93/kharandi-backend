from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import serializers
from core.permissions import IsAdmin
from core.utils import success_response, error_response
from .models import (News, SchoolRanking, StudyAbroad, Scholarship, TutorAd,
                     Notification, ReadingProgress)


# ─── Serializers ─────────────────────────────────────────────────────────────
class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = News
        fields = ["id","title","excerpt","content","category","color","date","created_at"]

class SchoolRankingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SchoolRanking
        fields = ["id","rank","name","location","school_type","score","year"]

class StudyAbroadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StudyAbroad
        fields = ["id","university","program_name","country","city","level","link"]

class ScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Scholarship
        fields = ["id","university","program_name","excerpt","country","city",
                  "level","link","deadline","is_active","created_at"]
        read_only_fields = ["id","created_at"]

class TutorAdSerializer(serializers.ModelSerializer):
    author_phone = serializers.CharField(source="user.phone", read_only=True)
    class Meta:
        model  = TutorAd
        fields = ["id","ad_type","subject","level","location","description",
                  "phone","author_name","author_phone","is_boosted","created_at"]
        read_only_fields = ["id","author_phone","created_at"]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ["id","title","message","notif_type","link","is_read","created_at"]

class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReadingProgress
        fields = ["document_id","progress","is_read","updated_at"]


# ─── News ─────────────────────────────────────────────────────────────────────
class NewsListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return success_response(
            data=NewsSerializer(News.objects.filter(is_published=True), many=True).data)
    def post(self, request):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        s = NewsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return success_response(data=s.data, status=201)

class NewsDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        try: obj = News.objects.get(id=pk)
        except News.DoesNotExist: return error_response("Article introuvable.", status=404)
        s = NewsSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data)
    def delete(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        try: News.objects.get(id=pk).delete()
        except News.DoesNotExist: return error_response("Article introuvable.", status=404)
        return success_response(message="Article supprimé.")


# ─── School Rankings ──────────────────────────────────────────────────────────
class SchoolRankingListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return success_response(data=SchoolRankingSerializer(SchoolRanking.objects.all(), many=True).data)
    def post(self, request):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        s = SchoolRankingSerializer(data=request.data)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data, status=201)


# ─── Study Abroad ─────────────────────────────────────────────────────────────
class StudyAbroadListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return success_response(data=StudyAbroadSerializer(StudyAbroad.objects.filter(is_active=True), many=True).data)
    def post(self, request):
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès refusé.", status=403)
        s = StudyAbroadSerializer(data=request.data)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data, status=201)


class SchoolRankingDetailView(APIView):
    """PATCH / DELETE /content/school-rankings/<uuid>/ — administration du palmares."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try: obj = SchoolRanking.objects.get(id=pk)
        except SchoolRanking.DoesNotExist:
            return error_response("Etablissement introuvable.", status=404)
        return success_response(data=SchoolRankingSerializer(obj).data)

    def patch(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        try: obj = SchoolRanking.objects.get(id=pk)
        except SchoolRanking.DoesNotExist:
            return error_response("Etablissement introuvable.", status=404)
        s = SchoolRankingSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data, message="Classement mis a jour.")

    def delete(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        deleted, _ = SchoolRanking.objects.filter(id=pk).delete()
        if not deleted:
            return error_response("Etablissement introuvable.", status=404)
        return success_response(message="Etablissement retire du palmares.")


class StudyAbroadDetailView(APIView):
    """PATCH / DELETE /content/study-abroad/<uuid>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try: obj = StudyAbroad.objects.get(id=pk)
        except StudyAbroad.DoesNotExist:
            return error_response("Programme introuvable.", status=404)
        return success_response(data=StudyAbroadSerializer(obj).data)

    def patch(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        try: obj = StudyAbroad.objects.get(id=pk)
        except StudyAbroad.DoesNotExist:
            return error_response("Programme introuvable.", status=404)
        s = StudyAbroadSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data, message="Programme mis a jour.")

    def delete(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        deleted, _ = StudyAbroad.objects.filter(id=pk).delete()
        if not deleted:
            return error_response("Programme introuvable.", status=404)
        return success_response(message="Programme supprime.")


# ─── Scholarships (bourses) ───────────────────────────────────────────────────
class ScholarshipListView(APIView):
    """GET /content/scholarships/ — liste publique des bourses.
    POST — creation reservee aux administrateurs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Scholarship.objects.filter(is_active=True)
        if c := request.query_params.get("country"):
            qs = qs.filter(country__icontains=c)
        if lv := request.query_params.get("level"):
            qs = qs.filter(level__icontains=lv)
        if q := request.query_params.get("search"):
            qs = qs.filter(university__icontains=q) | qs.filter(program_name__icontains=q)
        return success_response(data=ScholarshipSerializer(qs, many=True).data)

    def post(self, request):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        s = ScholarshipSerializer(data=request.data)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data, status=201, message="Bourse publiee.")


class ScholarshipDetailView(APIView):
    """GET / PATCH / DELETE /content/scholarships/<uuid>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try: obj = Scholarship.objects.get(id=pk)
        except Scholarship.DoesNotExist:
            return error_response("Bourse introuvable.", status=404)
        return success_response(data=ScholarshipSerializer(obj).data)

    def patch(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        try: obj = Scholarship.objects.get(id=pk)
        except Scholarship.DoesNotExist:
            return error_response("Bourse introuvable.", status=404)
        s = ScholarshipSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True); s.save()
        return success_response(data=s.data, message="Bourse mise a jour.")

    def delete(self, request, pk):
        if not IsAdmin().has_permission(request, self):
            return error_response("Acces refuse.", status=403)
        deleted, _ = Scholarship.objects.filter(id=pk).delete()
        if not deleted:
            return error_response("Bourse introuvable.", status=404)
        return success_response(message="Bourse supprimee.")


# ─── Tutor Ads ────────────────────────────────────────────────────────────────
class TutorAdListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = TutorAd.objects.filter(is_active=True).select_related("user")
        if t := request.query_params.get("type"):
            qs = qs.filter(ad_type=t)
        if s := request.query_params.get("subject"):
            qs = qs.filter(subject__icontains=s)
        if loc := request.query_params.get("location"):
            qs = qs.filter(location__icontains=loc)
        return success_response(data=TutorAdSerializer(qs, many=True).data)
    def post(self, request):
        s = TutorAdSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        profile = getattr(request.user, "profile", None)
        name = f"{profile.first_name} {profile.last_name}".strip() if profile else request.user.phone
        s.save(user=request.user, author_name=name)
        return success_response(data=s.data, status=201, message="Annonce publiée.")

class TutorAdDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, pk):
        try:
            ad = TutorAd.objects.get(id=pk)
            if ad.user != request.user and request.user.role != "ADMIN":
                return error_response("Accès refusé.", status=403)
            ad.delete()
            return success_response(message="Annonce supprimée.")
        except TutorAd.DoesNotExist:
            return error_response("Annonce introuvable.", status=404)


# ─── Notifications ────────────────────────────────────────────────────────────
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        notifs = Notification.objects.filter(user=request.user)
        return success_response(data=NotificationSerializer(notifs, many=True).data)

class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk=None):
        if pk:
            Notification.objects.filter(id=pk, user=request.user).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return success_response(message="Notifications marquées comme lues.")


# ─── Reading Progress ─────────────────────────────────────────────────────────
class ReadingProgressView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, document_id):
        try:
            p = ReadingProgress.objects.get(user=request.user, document_id=document_id)
            return success_response(data=ReadingProgressSerializer(p).data)
        except ReadingProgress.DoesNotExist:
            return success_response(data={"document_id": document_id, "progress": 0, "is_read": False})
    def post(self, request, document_id):
        progress = int(request.data.get("progress", 0))
        is_read  = request.data.get("is_read", False)
        obj, _   = ReadingProgress.objects.update_or_create(
            user=request.user, document_id=document_id,
            defaults={"progress": progress, "is_read": is_read},
        )
        return success_response(data=ReadingProgressSerializer(obj).data)
