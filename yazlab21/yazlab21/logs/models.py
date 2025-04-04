from django.db import models


class log(models.Model):
    log_date = models.DateTimeField(auto_now_add=True)
    log_type = models.TextField(max_length=10)
    log_message = models.TextField(max_length=250)

    def __str__(self):
        return self.log_message
