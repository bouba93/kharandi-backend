from django.urls import path
from .views import SendWelcomeView, SendCustomView
from .sse import NotificationStreamView

urlpatterns = [
    path("welcome/", SendWelcomeView.as_view(),       name="notify-welcome"),
    path("custom/",  SendCustomView.as_view(),         name="notify-custom"),
    path("stream/",  NotificationStreamView.as_view(), name="notify-stream"),
]
