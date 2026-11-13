from django.urls import path

from . import views

app_name = "viagens"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("viagens/nova/", views.criar, name="criar"),
    path("viagens/<int:pk>/editar/", views.editar, name="editar"),
    path("viagens/<int:pk>/", views.detalhe, name="detalhe"),
    path("viagens/<int:pk>/excluir/", views.excluir, name="excluir"),
    path("viagens/<int:pk>/situacao/<slug:para>/", views.mudar_estado, name="mudar_estado"),
    path("viagens/<int:pk>/atividades/nova/", views.criar_atividade, name="criar_atividade"),
    path(
        "viagens/<int:pk>/atividades/<int:atividade_pk>/editar/",
        views.editar_atividade,
        name="editar_atividade",
    ),
    path(
        "viagens/<int:pk>/atividades/<int:atividade_pk>/remover/",
        views.remover_atividade,
        name="remover_atividade",
    ),
    path(
        "viagens/<int:pk>/destinos/<int:destino_pk>/remover/",
        views.remover_destino,
        name="remover_destino",
    ),
]
