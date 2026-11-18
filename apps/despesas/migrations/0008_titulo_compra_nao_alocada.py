from django.db import migrations

TITULO = "Compra de moeda estrangeira não alocada"


def renomear_compras(apps, schema_editor):
    Despesa = apps.get_model("despesas", "Despesa")
    Despesa.objects.filter(movimento_saldo="compra").update(descricao=TITULO)


class Migration(migrations.Migration):
    dependencies = [
        ("despesas", "0007_despesa_cancelavel"),
    ]

    operations = [
        # Reverse is a no-op: the old titles included the balance name, which is not stored elsewhere.
        migrations.RunPython(renomear_compras, migrations.RunPython.noop),
    ]
