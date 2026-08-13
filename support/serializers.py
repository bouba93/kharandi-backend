from rest_framework import serializers
from .models import Ticket, TicketReply

class TicketReplySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.phone", read_only=True)
    class Meta:
        model  = TicketReply
        fields = ["id","author_name","message","is_staff","created_at"]

class TicketSerializer(serializers.ModelSerializer):
    replies     = TicketReplySerializer(many=True, read_only=True)
    reply_count = serializers.IntegerField(source="replies.count", read_only=True)
    class Meta:
        model  = Ticket
        fields = ["id","title","description","category","status","priority","replies","reply_count","created_at","updated_at"]
        read_only_fields = ["id","status","created_at","updated_at"]

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Ticket
        fields = ["title","description","category","priority"]
