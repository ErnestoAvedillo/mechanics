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
                        
                        if request.session.get('is_password_reset'):
                            # Es flujo de recuperación, no logueamos todavía, le pasamos a change_psw
                            del request.session['is_password_reset']
                            del request.session['verification_user_id']
                            request.session['reset_user_id'] = user.id
                            messages.success(request, "Código verificado. Introduce tu nueva contraseña.")
                            return redirect('change_psw')
                        else:
                            # Es flujo normal de registro
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


def recall_psw_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        print(f"Intento de recuperación para el email: '{email}'")
        
        # Usamos filter.first() para evitar MultipleObjectsReturned si hay correos duplicados
        user = User.objects.filter(email=email).first()
        
        if user:
            print(f"Usuario encontrado: {user.username} (ID: {user.id})")
            # Limpiamos el código anterior, porque es OneToOneField (evita IntegrityError)
            EmailVerification.objects.filter(user=user).delete()
            
            code = EmailVerification.generate_code()
            EmailVerification.objects.create(user=user, code=code)
            
            print(f"Código generado: {code} - Intentando enviar correo...")
            try:
                send_mail(
                    'Recuperación de contraseña - Mechanics',
                    f'Hola {user.username}, tu código para restablecer la contraseña es: {code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                print("Correo enviado exitosamente.")
            except Exception as e:
                print(f"Error crítico enviando correo: {e}")
                
            # Establecemos en sesión que este usuario va a recuperar contraseña
            request.session['verification_user_id'] = user.id
            request.session['is_password_reset'] = True
            
            messages.success(request, "Si el email ingresado corresponde a una cuenta registrada, se ha enviado un correo con instrucciones.")
            return redirect('verify_email')
        else:
            print(f"No se encontró ningún usuario con el correo: '{email}'")
            # Mensaje genérico por seguridad (evita honeypot de usuarios)
            messages.success(request, "Si el email ingresado corresponde a una cuenta registrada, se ha enviado un correo con instrucciones.")
            return redirect('login')
    
    return render(request, 'registration/recall_psw.html')


def change_psw_view(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            # Nota: el template actual de change_psw.html no tiene campo para current_password, 
            # pero aquí lo intentamos procesar si estuviera, o saltarlo.
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password1') # el id en change_psw.html es new_password1
            new_password_confirm = request.POST.get('new_password2')
            
            if new_password != new_password_confirm:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, 'registration/change_psw.html')
                
            # Si decides exigir la contraseña vieja en el template más adelante:
            # if not request.user.check_password(current_password):
            #     messages.error(request, "La contraseña actual es incorrecta.")
            #     return render(request, 'registration/change_psw.html')

            request.user.set_password(new_password)
            request.user.save()
            # Reiniciar sesión o usar update_session_auth_hash(request, request.user) 
            messages.success(request, "Contraseña cambiada con éxito.")
            return redirect('home')
        return render(request, 'registration/change_psw.html')
    
    elif 'reset_user_id' in request.session:
        user_id = request.session['reset_user_id']
        try:
            user = User.objects.get(id=user_id)
            if request.method == 'POST':
                new_password = request.POST.get('new_password1')
                new_password_confirm = request.POST.get('new_password2')
                
                if new_password != new_password_confirm:
                    messages.error(request, "Las contraseñas no coinciden.")
                    return render(request, 'registration/change_psw.html')
                
                user.set_password(new_password)
                user.save()
                del request.session['reset_user_id']
                messages.success(request, "Contraseña restablecida con éxito. Ahora puedes iniciar sesión.")
                # Opcional: podrías usar update_session_auth_hash si quieres que no se desconecte
                return redirect('login')
            return render(request, 'registration/change_psw.html')
        except User.DoesNotExist:
            messages.error(request, "Usuario no encontrado.")
            return redirect('login')
    else:
        return redirect('login')

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
    return json.JsonResponse({'status': 'ok'})


def bloques_editor(request):
    return render(request, 'menuapp/bloques_editor.html')


def json_visualizer(request):
    return render(request, 'menuapp/visualizador.html')
