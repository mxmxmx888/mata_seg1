import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0024_user_is_private"),
    ]

    operations = [
        migrations.CreateModel(
            name="FollowRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="follow_requests_sent", to=settings.AUTH_USER_MODEL)),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="follow_requests_received", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "follow_request",
            },
        ),
        migrations.AddConstraint(
            model_name="followrequest",
            constraint=models.UniqueConstraint(fields=("requester", "target"), name="uniq_follow_request_requester_target"),
        ),
        migrations.AddConstraint(
            model_name="followrequest",
            constraint=models.CheckConstraint(check=models.Q(("requester", models.F("target")), _negated=True), name="chk_follow_request_not_self"),
        ),
    ]
