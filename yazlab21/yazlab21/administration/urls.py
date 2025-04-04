from django.contrib import admindocs
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = "administration"

urlpatterns = [
    path("main-page/", views.index, name="main-page")
]