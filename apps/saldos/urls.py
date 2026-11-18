from django.urls import path

from . import views

app_name = "saldos"

urlpatterns = [
    path("nova-compra/", views.comprar, name="comprar"),
    path("compras/<int:pk>/editar/", views.editar_compra, name="editar_compra"),
    path("compras/<int:pk>/excluir/", views.excluir_compra, name="excluir_compra"),
]
