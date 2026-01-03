from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "0001_squashed_0037_recipepost_serves"),
    ]

    operations = [
        migrations.DeleteModel(name="Follows"),
    ]
