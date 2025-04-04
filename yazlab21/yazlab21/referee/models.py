from django.db import models
from author.models import BlurredPDF

class referee(models.Model):
    referee_name = models.TextField(max_length=20)
    referee_branch = models.TextField(max_length=50)

    def __str__(self):
        return self.referee_name

class RefereeEvaluation(models.Model):
    """
    Hakem değerlendirme modeli
    """
    blurred_pdf = models.ForeignKey(BlurredPDF, on_delete=models.CASCADE, related_name='evaluations')
    decision = models.CharField(max_length=20, choices=[
        ('success', 'Başarılı'),
        ('reject', 'Reddedildi')
    ])
    comments = models.TextField()
    evaluation_pdf_id = models.CharField(max_length=100, blank=True, null=True)
    evaluation_date = models.DateTimeField(auto_now_add=True)
    is_evaluation_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.blurred_pdf.original_article.article_name} - {self.get_decision_display()}"