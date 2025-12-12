from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0002_recipepost_ingredient'),  # adjust if needed
    ]

    operations = [
        migrations.AddField(
            model_name='recipepost',
            name='category',
            field=models.TextField(blank=True, null=True),
        ),
    ]