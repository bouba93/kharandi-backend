from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from core.utils import success_response, error_response

class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        q     = request.query_params.get("q","").strip()
        kind  = request.query_params.get("type","all")
        limit = min(int(request.query_params.get("limit",10)),50)
        if len(q) < 2: return error_response("Minimum 2 caractères.")
        results = {}
        if kind in ("docs","all"):
            from learning.models import Document
            docs = Document.objects.filter(Q(title__icontains=q)|Q(description__icontains=q))[:limit]
            results["documents"] = [{"id":str(d.id),"title":d.title,"level":d.level,"doc_type":d.doc_type,"is_free":d.is_free} for d in docs]
        if kind in ("qcm","all"):
            from learning.models import QCM
            qcms = QCM.objects.filter(user=request.user).filter(Q(subject__icontains=q)|Q(topic__icontains=q))[:limit]
            results["qcm"] = [{"id":str(q2.id),"subject":q2.subject,"topic":q2.topic,"score":q2.score} for q2 in qcms]
        return success_response(data={"query":q,"results":results})
