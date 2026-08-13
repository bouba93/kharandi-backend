# learning/views.py — CORRIGÉ
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from core.permissions import IsAdminOrReadOnly, IsAdmin
from core.utils import success_response, error_response
from core.redis_utils import bac_subjects_cache_get, bac_subjects_cache_set, bac_subjects_cache_clear
from .models import Document, Subject
from .serializers import DocumentSerializer, SubjectSerializer


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class   = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ["level", "doc_type", "is_free", "subject"]
    search_fields      = ["title", "description"]
    ordering           = ["-created_at"]

    def get_queryset(self):
        qs = Document.objects.select_related("subject").all()
        try:
            if not self.request.user.subscription.is_active():
                qs = qs.filter(is_free=True)
        except Exception:
            qs = qs.filter(is_free=True)
        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminOrReadOnly()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        from django.conf import settings
        doc = serializer.save()
        bac_subjects_cache_clear()

        if getattr(settings, "USE_CLOUDINARY", False):
            from core.cloudinary_utils import upload_document, upload_thumbnail
            file  = self.request.FILES.get("file")
            thumb = self.request.FILES.get("thumbnail")
            if file:
                file.seek(0)
                ctype  = "video" if doc.doc_type == "VIDEO" else "raw"
                result = upload_document(file, ctype)
                if result.get("url"):
                    doc.external_url = result["url"]
                    doc.file         = None
            if thumb:
                thumb.seek(0)
                result = upload_thumbnail(thumb)
                if result.get("url"):
                    doc.thumbnail = None
                    if not doc.external_url:
                        doc.external_url = result["url"]
            doc.save(update_fields=["external_url", "file", "thumbnail"])


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Document.objects.select_related("subject").all()
    serializer_class   = DocumentSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def perform_destroy(self, instance):
        from django.conf import settings
        if getattr(settings, "USE_CLOUDINARY", False) and instance.external_url:
            try:
                from core.cloudinary_utils import delete_file
                public_id = "/".join(instance.external_url.split("/")[-2:]).split(".")[0]
                delete_file(public_id)
            except Exception:
                pass
        instance.delete()


class SubjectListView(generics.ListAPIView):
    queryset           = Subject.objects.all()
    serializer_class   = SubjectSerializer
    permission_classes = [IsAuthenticated]


class DocumentUploadView(APIView):
    """POST /learning/documents/upload/ — Upload direct avec Cloudinary"""
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request):
        from core.permissions import IsAdmin
        if not IsAdmin().has_permission(request, self):
            return error_response("Accès réservé aux administrateurs.", status=403)

        title       = request.data.get("title", "").strip()
        doc_type    = request.data.get("doc_type", "COURS")
        level       = request.data.get("level", "")
        is_free     = request.data.get("is_free", "false").lower() == "true"
        description = request.data.get("description", "")
        subject_id  = request.data.get("subject")
        file        = request.FILES.get("file")
        thumbnail   = request.FILES.get("thumbnail")

        if not title:
            return error_response("Le titre est obligatoire.", status=400)

        subject = None
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                return error_response("Matière introuvable.", status=404)

        file_url  = None
        thumb_url = None

        from django.conf import settings
        if getattr(settings, "USE_CLOUDINARY", False):
            from core.cloudinary_utils import upload_document, upload_thumbnail
            if file:
                file.seek(0)
                ctype  = "video" if doc_type == "VIDEO" else "raw"
                result = upload_document(file, ctype)
                if not result.get("url"):
                    return error_response("Erreur lors de l'upload du fichier.", status=500)
                file_url = result["url"]
            if thumbnail:
                thumbnail.seek(0)
                result    = upload_thumbnail(thumbnail)
                thumb_url = result.get("url")

        doc = Document.objects.create(
            title=title, description=description, doc_type=doc_type,
            subject=subject, level=level, is_free=is_free,
            external_url=file_url or "",
        )

        return success_response(
            data=DocumentSerializer(doc, context={"request": request}).data,
            message="Document ajouté avec succès.",
            status=201,
        )
