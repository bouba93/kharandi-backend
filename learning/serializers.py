from rest_framework import serializers
from .models import Document, Subject, QCM


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Subject
        fields = ["id", "name", "icon"]


class DocumentSerializer(serializers.ModelSerializer):
    # Lecture : objet imbriqué
    subject    = SubjectSerializer(read_only=True)
    # Écriture : entier simple (évite le conflit source="subject")
    subject_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    file_url   = serializers.SerializerMethodField()

    class Meta:
        model  = Document
        fields = [
            "id", "title", "description", "doc_type",
            "subject", "subject_id",
            "level", "file", "file_url",
            "external_url", "thumbnail",
            "is_free", "price", "has_certification", "content",
            "downloads", "created_at",
        ]

    def get_file_url(self, obj):
        req = self.context.get("request")
        if obj.file and req:
            try: return req.build_absolute_uri(obj.file.url)
            except Exception: pass
        return obj.external_url or None

    def create(self, validated_data):
        subject_id = validated_data.pop("subject_id", None)
        doc = Document.objects.create(**validated_data)
        if subject_id:
            try:
                doc.subject_id = subject_id
                doc.save(update_fields=["subject"])
            except Exception:
                pass
        return doc

    def update(self, instance, validated_data):
        subject_id = validated_data.pop("subject_id", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if subject_id is not None:
            instance.subject_id = subject_id
        instance.save()
        return instance


class QCMSerializer(serializers.ModelSerializer):
    class Meta:
        model  = QCM
        fields = ["id","subject","level","topic","difficulty","questions","score","completed","created_at"]
