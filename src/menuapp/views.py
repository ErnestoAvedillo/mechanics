from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
import subprocess
import json
import csv
import os
import re
import base64
import hashlib
from .forms import SignupForm, VerificationForm
from .models import EmailVerification

URL_RE = re.compile(r'^(https?://)', re.IGNORECASE)
DATA_DIR = os.path.join(settings.BASE_DIR, "muelles", "static", "muelles", "data")


def open_show_folder(ruta):
    subprocess.Popen(f'explorer "{ruta}"')


def home(request):
    """Vista principal del proyecto"""
    return render(request, 'menuapp/index.html')


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()

            code = EmailVerification.generate_code()
            EmailVerification.objects.create(user=user, code=code)

            send_mail(
                'Tu código de verificación - Mechanics',
                f'Hola {user.username}, tu código de verificación es: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            request.session['verification_user_id'] = user.id
            return redirect('verify_email')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


def verify_email_view(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('signup')

    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(id=user_id)
                verification = EmailVerification.objects.get(user=user)
                
                if verification.code == form.cleaned_data['code']:
                    if not verification.is_expired():
                        user.is_active = True
                        user.save()
                        verification.is_verified = True
                        verification.save()
                        login(request, user)
                        messages.success(request, "¡Email verificado con éxito! Bienvenida/o.")
                        return redirect('home')
                    else:
                        messages.error(request, "El código ha expirado.")
                else:
                    messages.error(request, "Código incorrecto.")
            except (User.DoesNotExist, EmailVerification.DoesNotExist):
                return redirect('signup')
    else:
        form = VerificationForm()
    
    return render(request, 'registration/verify_email.html', {'form': form})

# El resto de vistas originales (contacto, editor, etc) se pueden añadir aquí
# basándote en el contenido original que preservamos antes.

def contacto(request):
    return render(request, 'menuapp/contacto.html')

def editor(request, datos, filename):
    return render(request, 'menuapp/editor.html', {'datos': datos, 'filename': filename})

def editor_with_session(request, data_id, filename):
    return render(request, 'menuapp/editor.html', {'data_id': data_id, 'filename': filename})

def abrir(request, filename):
    return redirect('editor', datos='dummy', filename=filename)

def abrir_carpeta(request, folder, group_name):
    return render(request, 'menuapp/index.html')

def guarda(request):
    return JsonResponse({'status': 'ok'})

def bloques_editor(request):
    return render(request, 'menuapp/bloques_editor.html')

def json_visualizer(request):
    return render(request, 'menuapp/visualizador.html')
