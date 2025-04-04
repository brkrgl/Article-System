from django.shortcuts import render
from django.contrib.sessions.models import Session

def index(request):
    Session.objects.all().delete()
    return render(request,"utils/index.html")
