import hashlib

from django.conf import settings
from django.core import signing
from rest_framework.permissions import BasePermission

from .models import School, SchoolTeacher


TOKEN_SALT = "kharandi.ecole.portal"


def _auth_hash(password_hash: str) -> str:
    return hashlib.sha256((password_hash or "").encode()).hexdigest()


def issue_portal_token(school: School, teacher: SchoolTeacher | None = None) -> str:
    actor_type = "teacher" if teacher else "school"
    actor_id = teacher.id if teacher else school.id
    password_hash = teacher.password_hash if teacher else school.password_hash
    return signing.dumps(
        {
            "actor_type": actor_type,
            "actor_id": str(actor_id),
            "school_id": str(school.id),
            "auth_hash": _auth_hash(password_hash),
        },
        salt=TOKEN_SALT,
        compress=True,
    )


def get_portal_context(request):
    if hasattr(request, "_school_portal_context"):
        return request._school_portal_context

    token = request.headers.get("X-School-Token", "").strip()
    authorization = request.headers.get("Authorization", "")
    if not token and authorization.startswith("School "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        request._school_portal_context = None
        return None

    try:
        payload = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=getattr(settings, "SCHOOL_TOKEN_MAX_AGE", 12 * 60 * 60),
        )
        school = School.objects.get(id=payload["school_id"], is_activated=True)
        actor_type = payload.get("actor_type")
        teacher = None
        if actor_type == "school":
            if str(school.id) != payload.get("actor_id"):
                raise signing.BadSignature("Invalid school actor")
            password_hash = school.password_hash
        elif actor_type == "teacher":
            teacher = SchoolTeacher.objects.get(
                id=payload.get("actor_id"), school=school
            )
            password_hash = teacher.password_hash
        else:
            raise signing.BadSignature("Invalid actor type")
        if payload.get("auth_hash") != _auth_hash(password_hash):
            raise signing.BadSignature("Token revoked")
    except (KeyError, ValueError, School.DoesNotExist, SchoolTeacher.DoesNotExist,
            signing.BadSignature, signing.SignatureExpired):
        request._school_portal_context = None
        return None

    request._school_portal_context = {
        "actor_type": actor_type,
        "school": school,
        "teacher": teacher,
    }
    return request._school_portal_context


def is_kharandi_admin(request) -> bool:
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.role == "ADMIN")


def has_school_access(request, school_id, school_admin_only=False) -> bool:
    if is_kharandi_admin(request):
        return True
    context = get_portal_context(request)
    if not context or str(context["school"].id) != str(school_id):
        return False
    return not school_admin_only or context["actor_type"] == "school"


class IsPortalOrKharandiAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_kharandi_admin(request) or get_portal_context(request) is not None


class IsSchoolAdminOrKharandiAdmin(BasePermission):
    def has_permission(self, request, view):
        if is_kharandi_admin(request):
            return True
        context = get_portal_context(request)
        return bool(context and context["actor_type"] == "school")
