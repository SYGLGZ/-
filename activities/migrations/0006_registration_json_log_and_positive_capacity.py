from django.db import migrations, models


def normalize_checkin_logs(apps, schema_editor):
    Registration = apps.get_model('activities', 'Registration')
    Registration.objects.filter(checkin_log__isnull=True).update(checkin_log='[]')
    Registration.objects.filter(checkin_log='').update(checkin_log='[]')


def normalize_empty_student_ids(apps, schema_editor):
    Profile = apps.get_model('activities', 'Profile')
    Profile.objects.filter(student_id='').update(student_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0005_registration_checkin_log_alter_activity_checkin_code_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_checkin_logs, migrations.RunPython.noop),
        migrations.RunPython(normalize_empty_student_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='profile',
            name='student_id',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='学号/工号'),
        ),
        migrations.AlterField(
            model_name='activity',
            name='capacity',
            field=models.PositiveIntegerField(default=100, verbose_name='人数限制'),
        ),
        migrations.AlterField(
            model_name='registration',
            name='checkin_log',
            field=models.JSONField(blank=True, default=list, help_text='记录签到操作的详细信息', verbose_name='签到日志'),
        ),
    ]
