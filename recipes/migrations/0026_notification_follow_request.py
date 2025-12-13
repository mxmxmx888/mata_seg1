import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0025_followrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="follow_request",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="recipes.followrequest"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(choices=[("like", "Like"), ("comment", "Comment"), ("follow", "Follow"), ("follow_request", "Follow Request"), ("tag", "Tag")], max_length=20),
        ),
    ]
