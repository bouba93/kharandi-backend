from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import serializers
from core.utils import success_response, error_response
from .models import Grade

class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    class Meta:
        model  = Grade
        fields = ["id","subject","grade_type","score","max_score","date",
                  "comment","student_name","teacher_name","created_at"]
        read_only_fields = ["id","student_name","teacher_name","created_at"]
    def get_student_name(self, obj):
        p = getattr(obj.student, "profile", None)
        return f"{p.first_name} {p.last_name}".strip() if (p and p.first_name) else obj.student.phone
    def get_teacher_name(self, obj):
        p = getattr(obj.teacher, "profile", None)
        return f"{p.first_name} {p.last_name}".strip() if (p and p.first_name) else obj.teacher.phone

class GradeListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        role = request.user.role
        if role == "TUTOR":
            qs = Grade.objects.filter(teacher=request.user).select_related("student__profile")
        else:
            qs = Grade.objects.filter(student=request.user).select_related("teacher__profile")
        return success_response(data=GradeSerializer(qs, many=True).data)
    def post(self, request):
        if request.user.role not in ["TUTOR", "ADMIN"]:
            return error_response("Seuls les tuteurs peuvent ajouter des notes.", status=403)
        from users.models import User
        student_id = request.data.get("student_id")
        if not student_id: return error_response("student_id obligatoire.", status=400)
        try: student = User.objects.get(id=student_id)
        except User.DoesNotExist: return error_response("Élève introuvable.", status=404)
        s = GradeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(teacher=request.user, student=student)
        return success_response(data=s.data, status=201, message="Note ajoutée.")

class StudentListView(APIView):
    """Renvoie la liste des élèves pour le tuteur."""
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.role not in ["TUTOR", "ADMIN"]:
            return error_response("Accès refusé.", status=403)
        from users.models import User
        students = User.objects.filter(role="STUDENT").select_related("profile")
        data = [{"id": str(u.id), "phone": u.phone,
                 "name": f"{getattr(u.profile,'first_name','')} {getattr(u.profile,'last_name','')}".strip() or u.phone}
                for u in students]
        return success_response(data=data)
