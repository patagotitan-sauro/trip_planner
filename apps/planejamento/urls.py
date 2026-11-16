from django.urls import path

from . import views

app_name = "planejamento"

urlpatterns = [
    path("", views.inicio, name="inicio"),
]
