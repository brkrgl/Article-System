from django.urls import path
from . import views

app_name = "referee"

urlpatterns = [
    path('panel/', views.referee_page, name="referee-page"),
    path('list/', views.referee_list, name='referee_list'),
    path('info/<int:referee_id>/', views.referee_info, name='referee_info'),
    path('assignment/<int:referee_id>/<str:article_id>/', views.referee_assignment, name='referee_assignment'),
    path('article/evaluate/<int:pdf_id>/', views.submit_evaluation, name='evaluate_article'),
    path('evaluation/submit/<int:pdf_id>/', views.submit_evaluation, name='submit_evaluation'),
    path('view-pdf/<str:file_id>/', views.view_pdf, name='view_pdf'),  # PDF görüntüleme için yeni URL
    path('dashboard/', views.dashboard, name='dashboard'),  # Dashboard URL'i
    path('article/preview-evaluation/<int:pdf_id>/', views.preview_evaluation, name='preview_evaluation'),
]