# Generated by Django 5.1.7 on 2025-03-25 00:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('author', '0008_article_to_review'),
    ]

    operations = [
        migrations.RenameField(
            model_name='article_to_review',
            old_name='article_drive_id',
            new_name='article',
        ),
        migrations.RemoveField(
            model_name='article_to_review',
            name='article_name',
        ),
        migrations.RemoveField(
            model_name='article_to_review',
            name='article_owner',
        ),
    ]
