from django.urls import path
from author.views import upload_article, article_status
from .views import *


app_name = "author"

urlpatterns = [
    path('upload_article/', upload_article, name='upload_article'),
    path('upload-file/', upload_file, name='upload-file'),  # Changed from upload_file to upload-file
    path('show_article/', show_article, name='show-article'),
    path('send_verification_code/', send_verification_code, name='send-verification-code'),
    path('check_article_status/', check_article_status, name='check-article-status'),
    path('article_status/', article_status, name='article-status'),  # New URL for the article status page
    path('message_to_editor/', message_to_editor, name='message-to-editor'),
    path('message_panel/', message_panel, name='message-panel'),
    path('get_user_messages/', get_user_messages, name='get-user-messages'),
    path('download_evaluation/<str:tracking_number>/', download_evaluation, name='download-evaluation'),
]