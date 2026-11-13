from django.urls import path

from . import views

app_name = "viagens"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("viagens/nova/", views.criar, name="criar"),
    path("viagens/<int:pk>/editar/", views.editar, name="editar"),
]
