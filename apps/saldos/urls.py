from django.urls import path

from . import views

app_name = "saldos"

urlpatterns = [
    path("nova-compra/", views.comprar, name="comprar"),
]
