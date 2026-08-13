"""
notifications/sse.py — Notifications temps réel via Server-Sent Events
────────────────────────────────────────────────────────────────────────
Endpoint : GET /api/v1/notifications/stream/

Le frontend s'abonne une fois. Dès qu'une notification est publiée
dans Redis (channel "notif:{user_id}"), elle est poussée au client
sans qu'il ait besoin de faire un nouveau GET.

Usage backend :
    from notifications.sse import push_notification
    push_notification(user_id, {"type": "payment", "message": "Paiement confirmé !"})

Usage frontend (JavaScript) :
    const es = new EventSource('/api/v1/notifications/stream/', {withCredentials: true});
    es.onmessage = (e) => console.log(JSON.parse(e.data));
"""
import json, logging, time
from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

PING_INTERVAL = 25   # secondes entre chaque ping (garde la connexion ouverte)


def push_notification(user_id: str, payload: dict):
    """
    Publie une notification dans Redis.
    Le stream SSE de l'utilisateur la reçoit en temps réel.
    """
    try:
        from django_redis import get_redis_connection
        r   = get_redis_connection("default")
        msg = json.dumps(payload, ensure_ascii=False)
        r.publish(f"notif:{user_id}", msg)
        logger.info("Notification publiée → user=%s type=%s", user_id, payload.get("type"))
    except Exception as exc:
        logger.error("Erreur push_notification user=%s : %s", user_id, exc)


class NotificationStreamView(APIView):
    """
    SSE endpoint — le client s'abonne et reçoit les notifications en push.
    GET /api/v1/notifications/stream/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.id)

        def event_stream():
            try:
                from django_redis import get_redis_connection
                r      = get_redis_connection("default")
                pubsub = r.pubsub()
                pubsub.subscribe(f"notif:{user_id}")
                logger.info("SSE ouvert pour user=%s", user_id)

                last_ping = time.time()

                for message in pubsub.listen():
                    # Ping toutes les 25s pour garder la connexion
                    now = time.time()
                    if now - last_ping > PING_INTERVAL:
                        yield ": ping\n\n"
                        last_ping = now

                    if message["type"] == "message":
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        yield f"data: {data}\n\n"

            except GeneratorExit:
                logger.info("SSE fermé pour user=%s", user_id)
            except Exception as exc:
                logger.error("Erreur SSE user=%s : %s", user_id, exc)
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"]     = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["Connection"]        = "keep-alive"
        return response
