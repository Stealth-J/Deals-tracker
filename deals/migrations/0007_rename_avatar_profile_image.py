# Generated by Django 5.2 on 2025-04-29 23:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('deals', '0006_profile'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='avatar',
            new_name='image',
        ),
    ]
