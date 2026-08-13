import uuid
from django.db import models

class Grade(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher      = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="given_grades")
    student      = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="received_grades")
    subject      = models.CharField(max_length=100)
    grade_type   = models.CharField(max_length=50, default="Devoir")
    score        = models.DecimalField(max_digits=5, decimal_places=2)
    max_score    = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    date         = models.DateField()
    comment      = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return f"{self.student.phone} — {self.subject}: {self.score}/{self.max_score}"
