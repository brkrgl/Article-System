# Generated by Django 5.1.2 on 2025-03-08 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('author', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UncensoredArticles',
            fields=[
                ('article_owner', models.EmailField(max_length=254)),
                ('article_name', models.CharField(max_length=255)),
                ('article_drive_id', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True)),
                ('tracking_number', models.CharField(max_length=20, unique=True)),
            ],
        ),
    ]
