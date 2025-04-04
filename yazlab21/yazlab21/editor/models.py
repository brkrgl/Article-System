from django.db import models
from author.models import Messages, UncensoredArticles
import json


class EditorReply(models.Model):
    original_message = models.ForeignKey(Messages, on_delete=models.CASCADE, related_name='replies')
    reply_to = models.EmailField()
    reply_subject = models.CharField(max_length=100)
    reply_text = models.TextField()
    reply_time = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Yanıt: {self.reply_subject}"
    
    class Meta:
        verbose_name = "Editör Yanıtı"
        verbose_name_plural = "Editör Yanıtları"
        ordering = ['-reply_time']


class ArticleKeywords(models.Model):
    """Makaleler için anahtar kelime depolama modeli"""
    article = models.OneToOneField(UncensoredArticles, on_delete=models.CASCADE, related_name='keyword_data')
    _keywords_json = models.TextField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    extraction_status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'İşleniyor'),
            ('completed', 'Tamamlandı'),
            ('failed', 'Başarısız')
        ],
        default='pending'
    )
    error_message = models.TextField(null=True, blank=True)
    
    @property
    def keywords(self):
        """JSON'dan anahtar kelimeleri döndür"""
        if self._keywords_json:
            try:
                return json.loads(self._keywords_json)
            except json.JSONDecodeError:
                return []
        return []
    
    @keywords.setter
    def keywords(self, value):
        """Anahtar kelimeleri JSON olarak kaydet"""
        if value is None:
            self._keywords_json = None
        else:
            self._keywords_json = json.dumps(value)
    
    def __str__(self):
        return f"Anahtar Kelimeler - {self.article}"
    
    class Meta:
        verbose_name = "Makale Anahtar Kelimeleri"
        verbose_name_plural = "Makale Anahtar Kelimeleri"



