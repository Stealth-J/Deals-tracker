# Generated by Django 5.2 on 2025-04-28 23:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deals', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deals',
            name='last_checked',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
