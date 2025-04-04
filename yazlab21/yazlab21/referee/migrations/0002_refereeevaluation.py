# Generated by Django 5.1.7 on 2025-03-28 00:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('author', '0011_blurredpdf_is_referee_assigned_and_more'),
        ('referee', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RefereeEvaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision', models.CharField(choices=[('success', 'Başarılı'), ('reject', 'Reddedildi')], max_length=20)),
                ('comments', models.TextField()),
                ('evaluation_pdf_id', models.CharField(blank=True, max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('blurred_pdf', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='author.blurredpdf')),
            ],
        ),
    ]
