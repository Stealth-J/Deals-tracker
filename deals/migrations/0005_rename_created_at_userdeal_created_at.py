# Generated by Django 5.2 on 2025-04-29 08:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('deals', '0004_userdeal'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userdeal',
            old_name='created_At',
            new_name='created_at',
        ),
    ]
