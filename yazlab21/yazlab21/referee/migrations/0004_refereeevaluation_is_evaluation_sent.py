# Generated by Django 5.1.7 on 2025-04-01 22:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('referee', '0003_rename_created_at_refereeevaluation_evaluation_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='refereeevaluation',
            name='is_evaluation_sent',
            field=models.BooleanField(default=False),
        ),
    ]
