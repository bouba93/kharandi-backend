"""
ecole/views.py — Kharandi École (API Django)
"""
import logging, uuid
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from core.utils import success_response, error_response
from .models import School, SchoolTeacher, SchoolStudent, SchoolClass, SchoolGrade, SchoolPayment, SchoolAbsence
from .permissions import (
    IsPortalOrKharandiAdmin,
    IsSchoolAdminOrKharandiAdmin,
    get_portal_context,
    has_school_access,
    is_kharandi_admin,
    issue_portal_token,
)

logger = logging.getLogger(__name__)


def _school_data(s, include_private=False):
    data = {
        "id": str(s.id), "name": s.name, "email": s.email,
        "is_activated": s.is_activated,
        "logo_url": s.logo_url, "phone": s.phone, "address": s.address,
        "subscription_active": s.subscription_active,
    }
    if include_private:
        data["code"] = s.code
    return data

def _teacher_data(t):
    return {"id": str(t.id), "name": t.name, "email": t.email,
            "classes": t.classes, "school_id": str(t.school_id)}

def _student_data(s):
    return {
        "id": str(s.id), "name": s.name, "matricule": s.matricule,
        "parent_phone": s.parent_phone,
        "classe": s.school_class.name if s.school_class else "",
        "school_id": str(s.school_id),
        "date_of_birth": str(s.date_of_birth) if s.date_of_birth else "",
    }


def _parent_can_access(request, student):
    if is_kharandi_admin(request):
        return True
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or user.role != "PARENT":
        return False
    user_phone = user.phone.replace(" ", "").replace("-", "")
    parent_phone = (student.parent_phone or "").replace(" ", "").replace("-", "")
    return bool(parent_phone and user_phone == parent_phone)


# ─── /ecole/schools/ ─────────────────────────────────────────────────────────
class SchoolListView(APIView):
    """
    GET  → liste toutes les écoles (admin) ou l'école d'un utilisateur
    POST → créer une nouvelle école (admin)
    """
    permission_classes = [IsPortalOrKharandiAdmin]

    def get(self, request):
        if is_kharandi_admin(request):
            schools = School.objects.all().order_by("name")
        else:
            schools = School.objects.filter(id=get_portal_context(request)["school"].id)
        return success_response(data=[_school_data(s) for s in schools])

    def post(self, request):
        if not is_kharandi_admin(request):
            return error_response("Accès réservé aux administrateurs.", status=403)
        name    = request.data.get("name",    "").strip()
        email   = request.data.get("email",   "").strip().lower()
        code    = request.data.get("code",    "").strip().upper()
        phone   = request.data.get("phone",   "").strip()
        address = request.data.get("address", "").strip()

        if not all([name, email, code]):
            return error_response("name, email et code sont requis.", status=400)

        if School.objects.filter(email=email).exists():
            return error_response("Une école avec cet email existe déjà.", status=400)
        if School.objects.filter(code=code).exists():
            return error_response("Ce code d'activation est déjà utilisé.", status=400)

        school = School.objects.create(
            name=name, email=email, code=code,
            phone=phone, address=address,
            is_activated=False,
            subscription_active=True,
        )
        logger.info("Nouvelle école créée : %s [%s]", name, code)
        return success_response(
            data=_school_data(school, include_private=True),
            message=f"École '{name}' créée.",
            status=201,
        )


# ─── /ecole/schools/<id>/ ─────────────────────────────────────────────────────
class SchoolDetailView(APIView):
    """GET/PATCH/DELETE une école par son ID."""
    permission_classes = [IsPortalOrKharandiAdmin]

    def get(self, request, school_id):
        if not has_school_access(request, school_id):
            return error_response("Accès refusé.", status=403)
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        return success_response(data=_school_data(school))

    def patch(self, request, school_id):
        if not has_school_access(request, school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        allowed_fields = ["name", "phone", "address", "logo_url"]
        if is_kharandi_admin(request):
            allowed_fields.append("subscription_active")
        for field in allowed_fields:
            if field in request.data:
                setattr(school, field, request.data[field])
        school.save()
        return success_response(data=_school_data(school), message="École mise à jour.")

    def delete(self, request, school_id):
        if not is_kharandi_admin(request):
            return error_response("Accès réservé aux administrateurs.", status=403)
        try:
            School.objects.get(id=school_id).delete()
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        return success_response(message="École supprimée.")



class ActivateSchoolView(APIView):
    """Première connexion — vérifie code + email, puis définit le mot de passe."""
    permission_classes = [AllowAny]

    def post(self, request):
        code     = request.data.get("code",     "").strip().upper()
        email    = request.data.get("email",    "").strip().lower()
        password = request.data.get("password", "").strip()

        try:
            school = School.objects.get(code=code, email=email)
        except School.DoesNotExist:
            return error_response("Code d'activation ou email incorrect.", status=404)

        if school.is_activated:
            return error_response("Cette école est déjà activée. Connectez-vous normalement.", status=400)

        if password:
            if len(password) < 6:
                return error_response("Le mot de passe doit avoir au moins 6 caractères.", status=400)
            school.set_password(password)
            school.is_activated = True
            school.save()
            return success_response(
                data=_school_data(school),
                message="École activée avec succès !",
            )

        # Première étape — vérifier sans mot de passe
        return success_response(
            data={"school_name": school.name},
            message="Code valide. Définissez votre mot de passe.",
        )


# ─── POST /ecole/login/ ──────────────────────────────────────────────────────
class SchoolLoginView(APIView):
    """Connexion direction — email + mot de passe."""
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email",    "").strip().lower()
        password = request.data.get("password", "").strip()

        try:
            school = School.objects.get(email=email)
        except School.DoesNotExist:
            return error_response("Identifiants incorrects.", status=401)

        if not school.is_activated:
            return error_response("Cette école n'est pas encore activée.", status=403)

        if not school.check_password(password):
            return error_response("Mot de passe incorrect.", status=401)

        if not school.subscription_active:
            return error_response("Abonnement école expiré. Contactez Kharandi.", status=403)

        return success_response(
            data={
                "type": "school",
                "profile": _school_data(school),
                "access_token": issue_portal_token(school),
            },
            message=f"Bienvenue, {school.name} !",
        )


# ─── POST /ecole/teacher/login/ ──────────────────────────────────────────────
class TeacherLoginView(APIView):
    """Connexion enseignant — email + mot de passe."""
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email",    "").strip().lower()
        password = request.data.get("password", "").strip()

        try:
            teacher = SchoolTeacher.objects.select_related("school").get(email=email)
        except SchoolTeacher.DoesNotExist:
            return error_response("Identifiants enseignant incorrects.", status=401)

        if not teacher.check_password(password):
            return error_response("Mot de passe incorrect.", status=401)

        return success_response(
            data={
                "type": "teacher",
                "profile": _teacher_data(teacher),
                "access_token": issue_portal_token(teacher.school, teacher=teacher),
            },
            message=f"Bienvenue, {teacher.name} !",
        )


# ─── GET /ecole/parent/<matricule>/ ─────────────────────────────────────────
class ParentLookupView(APIView):
    """Accès parent — recherche par matricule."""
    permission_classes = [IsAuthenticated]

    def get(self, request, matricule):
        try:
            student = SchoolStudent.objects.select_related("school", "school_class").get(
                matricule=matricule.upper()
            )
        except SchoolStudent.DoesNotExist:
            return error_response("Aucun élève trouvé avec ce matricule.", status=404)
        if not _parent_can_access(request, student):
            return error_response("Accès refusé.", status=403)

        # Récupérer les notes, paiements, absences
        grades   = [{"subject": g.subject, "value": g.value, "trimester": g.trimester, "comment": g.comment}
                    for g in student.grades.all()]
        payments = [{"label": p.label, "amount": str(p.amount), "is_paid": p.is_paid}
                    for p in student.payments.all()]
        absences = [{"date": str(a.date), "subject": a.subject, "justified": a.is_justified}
                    for a in student.absences.all()]

        return success_response(data={
            "student":  _student_data(student),
            "grades":   grades,
            "payments": payments,
            "absences": absences,
            "school":   _school_data(student.school),
        })


# ─── /ecole/schools/<id>/students/ ──────────────────────────────────────────
class StudentListView(APIView):
    permission_classes = [IsPortalOrKharandiAdmin]

    def get(self, request, school_id):
        if not has_school_access(request, school_id):
            return error_response("Accès refusé.", status=403)
        students = SchoolStudent.objects.filter(school_id=school_id).select_related("school_class")
        return success_response(data=[_student_data(s) for s in students])

    def post(self, request, school_id):
        if not has_school_access(request, school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)

        name         = request.data.get("name",          "").strip()
        classe_name  = request.data.get("classe",        "").strip()
        parent_phone = request.data.get("parent_phone",  "").strip()
        dob          = request.data.get("date_of_birth", None)

        if not name:
            return error_response("Nom de l'élève requis.", status=400)

        # Récupérer ou créer la classe
        school_class = None
        if classe_name:
            school_class, _ = SchoolClass.objects.get_or_create(school=school, name=classe_name)

        # Générer un matricule unique
        matricule = f"KHA-{school.code[:4]}-{uuid.uuid4().hex[:4].upper()}"

        student = SchoolStudent.objects.create(
            school=school, school_class=school_class,
            name=name, matricule=matricule,
            parent_phone=parent_phone,
            date_of_birth=dob or None,
        )
        return success_response(data=_student_data(student), status=201,
                                message=f"Élève ajouté. Matricule : {matricule}")


# ─── /ecole/students/<id>/ ───────────────────────────────────────────────────
class StudentDetailView(APIView):
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def patch(self, request, student_id):
        try:
            student = SchoolStudent.objects.get(id=student_id)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable.", status=404)
        if not has_school_access(request, student.school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        for field in ["name", "parent_phone"]:
            if field in request.data:
                setattr(student, field, request.data[field])
        if "classe" in request.data:
            c, _ = SchoolClass.objects.get_or_create(school=student.school, name=request.data["classe"])
            student.school_class = c
        student.save()
        return success_response(data=_student_data(student))

    def delete(self, request, student_id):
        try:
            student = SchoolStudent.objects.get(id=student_id)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable.", status=404)
        if not has_school_access(request, student.school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        student.delete()
        return success_response(message="Élève supprimé.")


# ─── /ecole/grades/ ──────────────────────────────────────────────────────────
class GradeView(APIView):
    permission_classes = [IsPortalOrKharandiAdmin]

    def get(self, request):
        student_id = request.query_params.get("student_id")
        school_id  = request.query_params.get("school_id")
        context = get_portal_context(request)
        qs = SchoolGrade.objects.select_related("student")
        if context:
            qs = qs.filter(student__school=context["school"])
        if student_id: qs = qs.filter(student_id=student_id)
        if school_id:
            if not has_school_access(request, school_id):
                return error_response("Accès refusé.", status=403)
            qs = qs.filter(student__school_id=school_id)
        data = [{"id": str(g.id), "student_name": g.student.name, "subject": g.subject,
                 "value": g.value, "trimester": g.trimester, "comment": g.comment} for g in qs]
        return success_response(data=data)

    def post(self, request):
        student_id = request.data.get("student_id")
        subject    = request.data.get("subject", "").strip()
        value      = request.data.get("value")
        trimester  = request.data.get("trimester", "T1")
        comment    = request.data.get("comment", "")
        teacher_id = request.data.get("teacher_id")

        if not all([student_id, subject, value is not None]):
            return error_response("student_id, subject et value requis.", status=400)

        try:
            student = SchoolStudent.objects.get(id=student_id)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable.", status=404)
        if not has_school_access(request, student.school_id):
            return error_response("Accès refusé.", status=403)

        teacher = None
        context = get_portal_context(request)
        if context and context["actor_type"] == "teacher":
            teacher = context["teacher"]
        elif teacher_id:
            teacher = SchoolTeacher.objects.filter(
                id=teacher_id, school=student.school
            ).first()

        grade = SchoolGrade.objects.create(
            student=student, teacher=teacher, subject=subject,
            value=float(value), trimester=trimester, comment=comment,
        )
        return success_response(
            data={"id": str(grade.id), "subject": grade.subject, "value": grade.value},
            status=201, message="Note ajoutée."
        )


# ─── /ecole/payments/ ────────────────────────────────────────────────────────
class PaymentView(APIView):
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def get(self, request):
        school_id = request.query_params.get("school_id")
        context = get_portal_context(request)
        qs = SchoolPayment.objects.select_related("student")
        if context:
            qs = qs.filter(student__school=context["school"])
        if school_id:
            if not has_school_access(request, school_id, school_admin_only=True):
                return error_response("Accès refusé.", status=403)
            qs = qs.filter(student__school_id=school_id)
        data = [{"id": str(p.id), "student_name": p.student.name, "label": p.label,
                 "amount": str(p.amount), "is_paid": p.is_paid,
                 "paid_at": str(p.paid_at) if p.paid_at else None} for p in qs]
        return success_response(data=data)

    def post(self, request):
        student_id = request.data.get("student_id")
        label      = request.data.get("label", "Scolarité").strip()
        amount     = request.data.get("amount", 0)
        is_paid    = request.data.get("is_paid", False)

        try:
            student = SchoolStudent.objects.get(id=student_id)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable.", status=404)
        if not has_school_access(request, student.school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        p = SchoolPayment.objects.create(
            student=student, label=label, amount=amount, is_paid=is_paid,
            paid_at=timezone.now() if is_paid else None,
        )
        return success_response(data={"id": str(p.id)}, status=201, message="Paiement enregistré.")

    def patch(self, request, payment_id):
        try:
            p = SchoolPayment.objects.get(id=payment_id)
        except SchoolPayment.DoesNotExist:
            return error_response("Paiement introuvable.", status=404)
        if not has_school_access(request, p.student.school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        p.is_paid = True
        p.paid_at = timezone.now()
        p.save(update_fields=["is_paid", "paid_at"])
        return success_response(message="Paiement marqué comme payé.")


# ─── /ecole/absences/ ────────────────────────────────────────────────────────
class AbsenceView(APIView):
    permission_classes = [IsPortalOrKharandiAdmin]

    def get(self, request):
        school_id = request.query_params.get("school_id")
        context = get_portal_context(request)
        qs = SchoolAbsence.objects.select_related("student")
        if context:
            qs = qs.filter(student__school=context["school"])
        if school_id:
            if not has_school_access(request, school_id):
                return error_response("Accès refusé.", status=403)
            qs = qs.filter(student__school_id=school_id)
        data = [{"id": str(a.id), "student_name": a.student.name, "date": str(a.date),
                 "subject": a.subject, "justified": a.is_justified} for a in qs]
        return success_response(data=data)

    def post(self, request):
        student_id   = request.data.get("student_id")
        date         = request.data.get("date")
        subject      = request.data.get("subject", "")
        is_justified = request.data.get("is_justified", False)

        try:
            student = SchoolStudent.objects.get(id=student_id)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable.", status=404)
        if not has_school_access(request, student.school_id):
            return error_response("Accès refusé.", status=403)

        a = SchoolAbsence.objects.create(
            student=student, date=date, subject=subject, is_justified=is_justified
        )
        return success_response(data={"id": str(a.id)}, status=201, message="Absence enregistrée.")


# ─── /ecole/teachers/ ────────────────────────────────────────────────────────
class TeacherListView(APIView):
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def get(self, request, teacher_id=None):
        school_id = request.query_params.get("school_id")
        context = get_portal_context(request)
        qs = SchoolTeacher.objects.all()
        if context:
            qs = qs.filter(school=context["school"])
        if school_id:
            if not has_school_access(request, school_id, school_admin_only=True):
                return error_response("Accès refusé.", status=403)
            qs = qs.filter(school_id=school_id)
        if teacher_id:
            qs = qs.filter(id=teacher_id)
        return success_response(data=[_teacher_data(t) for t in qs])

    def post(self, request):
        school_id = request.data.get("school_id")
        name      = request.data.get("name",     "").strip()
        email     = request.data.get("email",    "").strip().lower()
        password  = request.data.get("password", "").strip()
        classes   = request.data.get("classes",  [])

        if not all([school_id, name, email, password]):
            return error_response("school_id, name, email et password requis.", status=400)
        if len(password) < 8:
            return error_response("Le mot de passe doit contenir au moins 8 caractères.", status=400)

        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        if not has_school_access(request, school.id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        if SchoolTeacher.objects.filter(email=email).exists():
            return error_response("Un enseignant avec cet email existe déjà.", status=400)

        teacher = SchoolTeacher(school=school, name=name, email=email, classes=classes)
        teacher.set_password(password)
        teacher.save()
        return success_response(data=_teacher_data(teacher), status=201,
                                message=f"Enseignant {name} créé.")

    def delete(self, request, teacher_id):
        try:
            teacher = SchoolTeacher.objects.get(id=teacher_id)
        except SchoolTeacher.DoesNotExist:
            return error_response("Enseignant introuvable.", status=404)
        if not has_school_access(request, teacher.school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        teacher.delete()
        return success_response(message="Enseignant supprimé.")


# ─── /ecole/classes/ ─────────────────────────────────────────────────────────
class ClassListView(APIView):
    permission_classes = [IsPortalOrKharandiAdmin]

    def get(self, request):
        school_id = request.query_params.get("school_id")
        context = get_portal_context(request)
        qs = SchoolClass.objects.all()
        if context:
            qs = qs.filter(school=context["school"])
        if school_id:
            if not has_school_access(request, school_id):
                return error_response("Accès refusé.", status=403)
            qs = qs.filter(school_id=school_id)
        return success_response(data=[{"id": str(c.id), "name": c.name} for c in qs])

    def post(self, request):
        school_id = request.data.get("school_id")
        name      = request.data.get("name", "").strip()
        if not all([school_id, name]):
            return error_response("school_id et name requis.", status=400)
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        if not has_school_access(request, school.id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        c, created = SchoolClass.objects.get_or_create(school=school, name=name)
        return success_response(data={"id": str(c.id), "name": c.name},
                                status=201 if created else 200)


# ══════════════════════════════════════════════════════════════════════════════
# ABONNEMENTS — /ecole/subscriptions/
# ══════════════════════════════════════════════════════════════════════════════

class SubscriptionPricingView(APIView):
    """GET /ecole/subscriptions/pricing — Tarifs en vigueur"""
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import SchoolSubscription as Sub
        return success_response(data={
            "base_price_per_student_annual_gnf":   Sub.BASE_PRICE_PER_STUDENT,
            "badges_option_price_per_student_annual_gnf": Sub.BADGES_PRICE_PER_STUDENT,
            "min_students": Sub.MIN_STUDENTS,
        })


class SubscriptionCheckoutView(APIView):
    """POST /ecole/subscriptions/checkout-session — Initialiser un paiement"""
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def post(self, request):
        from .models import SchoolSubscription as Sub, School
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta

        school_id      = request.data.get("school_id", "")
        student_count  = int(request.data.get("student_count", 0))
        badges         = bool(request.data.get("unlocked_badges_option", False))
        payment_method = request.data.get("payment_method", "").strip()

        if not school_id:
            return error_response("school_id requis.", status=400)
        if student_count < Sub.MIN_STUDENTS:
            return error_response(
                f"Minimum {Sub.MIN_STUDENTS} élèves requis.", status=400)

        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        if not has_school_access(request, school.id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        amount = Sub.compute_amount(student_count, badges)

        sub = Sub.objects.create(
            school                 = school,
            status                 = Sub.Status.PENDING,
            student_count          = student_count,
            unlocked_badges_option = badges,
            payment_method         = payment_method,
            amount_gnf             = amount,
        )

        # Simuler une URL de paiement (à remplacer par LengoPay ou Orange Money API)
        payment_url = f"https://pay.kharandi.gn/checkout/{sub.id}"

        return success_response(
            data={
                "subscription_id":  str(sub.id),
                "amount_gnf":       amount,
                "student_count":    student_count,
                "badges_option":    badges,
                "payment_method":   payment_method,
                "payment_url":      payment_url,
                "status":           "pending",
                "message":          "Procédez au paiement via le lien fourni ou attendez la confirmation USSD.",
            },
            status=201,
        )


class SubscriptionStatusView(APIView):
    """GET /ecole/subscriptions/status/<school_id>"""
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def get(self, request, school_id):
        from .models import SchoolSubscription as Sub, School
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        if not has_school_access(request, school.id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        sub = (Sub.objects
               .filter(school=school, status=Sub.Status.ACTIVE)
               .order_by("-created_at")
               .first())

        if not sub:
            return success_response(data={
                "school_id":             str(school_id),
                "subscription_status":   "none",
                "expires_at":            None,
                "unlocked_badges_option":False,
                "student_license_quota": 0,
                "student_license_used":  school.students.count(),
            })

        return success_response(data={
            "school_id":             str(school_id),
            "subscription_status":   sub.status,
            "expires_at":            sub.expires_at.isoformat() if sub.expires_at else None,
            "unlocked_badges_option":sub.unlocked_badges_option,
            "student_license_quota": sub.student_count,
            "student_license_used":  school.students.count(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# BADGES — /ecole/schools/badges/
# ══════════════════════════════════════════════════════════════════════════════

def _badge_data(b):
    return {
        "id":        str(b.id),
        "school_id": str(b.school_id),
        "student_id":str(b.student_id),
        "student":   b.student.name,
        "title":     b.title,
        "category":  b.category,
        "message":   b.message,
        "signatory": b.signatory,
        "date":      b.issued_at.date().isoformat(),
    }


class BadgeIssueView(APIView):
    """POST /ecole/schools/badges/issue — Décerner un badge"""
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def post(self, request):
        from .models import SchoolBadge, School, SchoolStudent, SchoolSubscription as Sub
        school_id  = request.data.get("school_id", "")
        student_id = request.data.get("student_id", "")
        title      = request.data.get("title", "").strip()
        category   = request.data.get("category", "Gold").strip()
        message    = request.data.get("message", "").strip()
        signatory  = request.data.get("signatory", "").strip()

        if not all([school_id, student_id, title]):
            return error_response("school_id, student_id et title sont requis.", status=400)

        try:
            school  = School.objects.get(id=school_id)
            student = SchoolStudent.objects.get(id=student_id, school=school)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable dans cette école.", status=404)
        if not has_school_access(request, school.id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        # Vérifier que l'option badges est activée
        active_sub = (Sub.objects
                      .filter(school=school, status=Sub.Status.ACTIVE)
                      .order_by("-created_at").first())
        if active_sub and not active_sub.unlocked_badges_option:
            return error_response(
                "L'option Badges/Certificats n'est pas activée pour cet établissement.",
                status=403,
            )

        if category not in [c[0] for c in SchoolBadge.Category.choices]:
            category = "Gold"

        badge = SchoolBadge.objects.create(
            school    = school,
            student   = student,
            title     = title,
            category  = category,
            message   = message,
            signatory = signatory,
        )
        return success_response(data=_badge_data(badge), status=201)


class BadgeHistoryView(APIView):
    """GET /ecole/schools/badges/history/<school_id>"""
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def get(self, request, school_id):
        from .models import SchoolBadge, School
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return error_response("École introuvable.", status=404)
        if not has_school_access(request, school.id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)

        badges = SchoolBadge.objects.filter(school=school).select_related("student")
        return success_response(data=[_badge_data(b) for b in badges])


class BadgeDetailView(APIView):
    """DELETE /ecole/schools/badges/<badge_id> — Révoquer un badge"""
    permission_classes = [IsSchoolAdminOrKharandiAdmin]

    def delete(self, request, badge_id):
        from .models import SchoolBadge
        try:
            badge = SchoolBadge.objects.get(id=badge_id)
        except SchoolBadge.DoesNotExist:
            return error_response("Badge introuvable.", status=404)
        if not has_school_access(request, badge.school_id, school_admin_only=True):
            return error_response("Accès refusé.", status=403)
        badge.delete()
        return success_response(message="Badge révoqué.")


# ══════════════════════════════════════════════════════════════════════════════
# PARENTS — /ecole/parents/
# ══════════════════════════════════════════════════════════════════════════════

class ParentStudentBadgesView(APIView):
    """GET /ecole/parents/students/<student_id>/badges"""
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        from .models import SchoolBadge, SchoolStudent
        try:
            student = SchoolStudent.objects.get(id=student_id)
        except SchoolStudent.DoesNotExist:
            return error_response("Élève introuvable.", status=404)
        if not _parent_can_access(request, student):
            return error_response("Accès refusé.", status=403)

        badges = SchoolBadge.objects.filter(student=student)
        return success_response(data=[_badge_data(b) for b in badges])


class ParentBadgePDFView(APIView):
    """GET /ecole/parents/students/<student_id>/badges/<badge_id>/pdf"""
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id, badge_id):
        from .models import SchoolBadge, SchoolStudent
        from django.http import HttpResponse
        import io

        try:
            student = SchoolStudent.objects.get(id=student_id)
            badge   = SchoolBadge.objects.get(id=badge_id, student=student)
        except (SchoolStudent.DoesNotExist, SchoolBadge.DoesNotExist):
            return error_response("Badge ou élève introuvable.", status=404)
        if not _parent_can_access(request, student):
            return error_response("Accès refusé.", status=403)

        try:
            from weasyprint import HTML
            html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Georgia', serif; background: #fff; margin: 0; padding: 40px; }}
  .cert {{ border: 8px double #c8a84b; padding: 40px; text-align: center; max-width: 700px; margin: auto; }}
  .badge-cat {{ font-size: 48px; margin: 10px 0; }}
  .title {{ font-size: 28px; font-weight: bold; color: #1a1a2e; margin: 20px 0 10px; }}
  .school {{ font-size: 16px; color: #555; margin-bottom: 20px; }}
  .student {{ font-size: 22px; font-weight: bold; color: #c8a84b; margin: 20px 0; }}
  .message {{ font-size: 15px; color: #333; font-style: italic; margin: 20px 0; line-height: 1.6; }}
  .signatory {{ margin-top: 40px; font-size: 14px; color: #444; }}
  .date {{ font-size: 12px; color: #888; margin-top: 10px; }}
  .kharandi {{ font-size: 11px; color: #bbb; margin-top: 30px; }}
</style>
</head>
<body>
<div class="cert">
  <div class="badge-cat">{'🥇' if badge.category == 'Gold' else '🥈' if badge.category == 'Silver' else '🥉' if badge.category == 'Bronze' else '🏅'}</div>
  <div class="title">{badge.title}</div>
  <div class="school">{badge.school.name}</div>
  <div>Décerné à</div>
  <div class="student">{student.name}</div>
  <div class="message">« {badge.message} »</div>
  <div class="signatory">{badge.signatory}</div>
  <div class="date">Le {badge.issued_at.strftime('%d/%m/%Y')}</div>
  <div class="kharandi">Généré par Kharandi École — kharandi.gn</div>
</div>
</body>
</html>"""
            pdf_bytes = HTML(string=html_content).write_pdf()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="badge_{badge_id[:8]}.pdf"'
            )
            return response

        except Exception as e:
            logger.error("Badge PDF error: %s", e)
            return error_response("Impossible de générer le PDF.", status=503)
