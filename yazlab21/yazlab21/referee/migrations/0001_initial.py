# Generated by Django 5.1.7 on 2025-03-25 00:50

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='referee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('referee_name', models.TextField(max_length=20)),
                ('referee_branch', models.TextField(max_length=50)),
            ],
        ),
    ]
