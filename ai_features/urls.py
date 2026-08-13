from django.urls import path
from .views import (
    AIStatusView, AIAskView, AIAskStreamView,
    AIAskImageView, GenerateQCMView, SubmitQCMView,
)

urlpatterns = [
    path("status/",                    AIStatusView.as_view(),    name="ai-status"),
    path("ask/",                       AIAskView.as_view(),       name="ai-ask"),
    path("ask/stream/",                AIAskStreamView.as_view(), name="ai-ask-stream"),
    path("ask-image/",                 AIAskImageView.as_view(),  name="ai-ask-image"),
    path("generate-qcm/",              GenerateQCMView.as_view(), name="ai-generate-qcm"),
    path("qcm/<uuid:qcm_id>/submit/",  SubmitQCMView.as_view(),   name="ai-submit-qcm"),
]
