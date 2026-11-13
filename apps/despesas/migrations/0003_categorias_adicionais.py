from django.db import migrations

# The owner's imported categories stay; only the missing ones are added.
CATEGORIAS = ["Alimentação", "Compras", "Seguro", "Outros"]


def criar_categorias(apps, schema_editor):
    Categoria = apps.get_model("despesas", "Categoria")
    for nome in CATEGORIAS:
        Categoria.objects.get_or_create(nome=nome)


class Migration(migrations.Migration):
    dependencies = [
        ("despesas", "0002_despesa_data"),
    ]

    operations = [
        # Reverse is a no-op: the categories may already be used by expenses.
        migrations.RunPython(criar_categorias, migrations.RunPython.noop),
    ]
