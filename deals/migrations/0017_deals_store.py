# Generated by Django 5.2 on 2025-06-27 16:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deals', '0016_deals_image_path_deals_price_text_alter_deals_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='deals',
            name='store',
            field=models.CharField(choices=[('test', 'Test'), ('jumia', 'Jumia'), ('konga', 'Konga')], default='test', max_length=10),
        ),
    ]
