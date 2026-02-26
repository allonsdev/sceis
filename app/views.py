from django.shortcuts import render, get_object_or_404
from app.models import *


def home(request):
    return render(request, "landing/index.html")

def login(request):
    return render(request, "dashboard/login.html")

def dashboard(request):
    return render(request, "dashboard/index.html")

def scan_qr(request):

    return render(request, 'animal_detail.html', context)
