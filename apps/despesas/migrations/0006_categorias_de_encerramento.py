from django.db import migrations

# RN-14: where the unallocated balance goes when a trip is completed.
CATEGORIAS = ["Outros gastos de cartão pré-pago", "Outros gastos com dinheiro"]


def criar_categorias(apps, schema_editor):
    Categoria = apps.get_model("despesas", "Categoria")
    for nome in CATEGORIAS:
        Categoria.objects.get_or_create(nome=nome)


class Migration(migrations.Migration):
    dependencies = [
        ("despesas", "0005_despesa_saldo"),
    ]

    operations = [
        # Reverse is a no-op: the categories may already be used by expenses.
        migrations.RunPython(criar_categorias, migrations.RunPython.noop),
    ]
