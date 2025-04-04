from django.urls import path
from . import views

app_name = 'editor'

urlpatterns = [
    path('', views.editor_page, name='editor_page'),
    path('download_pdf/<str:drive_id>/', views.download_pdf, name='download_pdf'),
    path('view_article/<str:drive_id>/', views.view_article, name='view_article'),
    path('get_article_keywords/', views.get_article_keywords, name='get_article_keywords'),
    path('assign_referee/', views.assign_referee_page, name='assign_referee'),
    path('assign_referee_action/', views.assign_referee_action, name='assign_referee_action'),
    path('get_referees_by_category/', views.get_referees_by_category, name='get_referees_by_category'),
    path("hide_personal_info/", views.hide_personal_info, name="hide_personal_info"),
    path("get_blurred_status/<str:article_drive_id>/", views.get_blurred_status, name="get_blurred_status"),
    path('messages/', views.author_messages, name='author_messages'),
    path('send_reply_to_author/', views.send_reply_to_author, name='send_reply_to_author'),
    path('list_articles/', views.list_articles, name='list_articles'),
    path('approve_evaluation/<int:evaluation_id>/', views.approve_evaluation, name='approve_evaluation'),
    path('download_evaluation_pdf/<int:evaluation_id>/', views.download_evaluation_pdf, name='download_evaluation_pdf'),
    path('logs/', views.log_view, name='log_view'),
]