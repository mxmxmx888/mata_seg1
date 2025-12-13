from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0023_merge_20251212_2018"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_private",
            field=models.BooleanField(default=False),
        ),
    ]
