from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progress", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprogress",
            name="started_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when the user first started or resumed this course.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="userprogress",
            name="unenrolled_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when the user paused participation without deleting history.",
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="userprogress",
            index=models.Index(
                fields=["user", "unenrolled_at"],
                name="idx_progress_user_active",
            ),
        ),
    ]
