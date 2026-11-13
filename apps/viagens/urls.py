from django.urls import path

from . import views

app_name = "viagens"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("viagens/nova/", views.criar, name="criar"),
    path("viagens/<int:pk>/editar/", views.editar, name="editar"),
    path("viagens/<int:pk>/", views.detalhe, name="detalhe"),
    path("viagens/<int:pk>/excluir/", views.excluir, name="excluir"),
    path(
        "viagens/<int:pk>/destinos/<int:destino_pk>/remover/",
        views.remover_destino,
        name="remover_destino",
    ),
]
