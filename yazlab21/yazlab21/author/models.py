from django.db import models
from django.utils import timezone

class VerificationCode(models.Model):
    email = models.EmailField(unique=True)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class UncensoredArticles(models.Model):
    article_owner = models.EmailField() 
    article_name = models.CharField(max_length=255)
    article_drive_id = models.CharField(max_length=50, unique=True, primary_key=True)
    tracking_number = models.CharField(max_length=20, unique=True)
    article_finish = models.BooleanField(default=False)
    article_status = models.CharField(max_length=50, default="Hakem ataması bekleniyor.")
    uploaded_at = models.DateTimeField(default=timezone.now)  # default değer eklendi

    def __str__(self):
        return f"{self.article_name} - {self.tracking_number}"
    
class BlurredPDF(models.Model):
    original_article = models.OneToOneField(
        UncensoredArticles, 
        on_delete=models.CASCADE, 
        related_name='blurred_pdf'
    )
    blurred_drive_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_referee_assigned = models.BooleanField(default=False)
    referee_name = models.TextField(max_length=50,default="Hakem ataması bekleniyor.")

    def __str__(self):
        return f"Blurred PDF for {self.original_article.article_name}"

class Messages(models.Model):
    message_sender_email = models.EmailField()
    message_time = models.DateTimeField(auto_now_add=True)
    message_title = models.CharField(max_length=100)  # Uzunluk 50'den 100'e çıkarıldı
    message_text = models.TextField(max_length=1000)  # CharField'dan TextField'a değiştirildi ve uzunluk artırıldı
    is_read = models.BooleanField(default=False)
    is_from_author = models.BooleanField(default=True)  # True: Yazardan editöre, False: Editörden yazara
    
    def __str__(self):
        return f"{self.message_sender_email} - {self.message_title}"
    
    class Meta:
        verbose_name = "Mesaj"
        verbose_name_plural = "Mesajlar"
        ordering = ['-message_time']