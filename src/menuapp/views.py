from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.translation import gettext as _
import subprocess
import json
import csv
import os
import re
import base64
import hashlib
from .forms import SignupForm, VerificationForm, ProfileForm
from specs.demo import is_demo
from .models import EmailVerification, PrivacyConsent
import logging

logging.basicConfig(level=logging.INFO)
URL_RE = re.compile(r'^(https?://)', re.IGNORECASE)
DATA_DIR = os.path.join(settings.BASE_DIR, "muelles", "static", "muelles", "data")


def open_show_folder(ruta):
    subprocess.Popen(f'explorer "{ruta}"')


def home(request):
    """Main project view"""
    return render(request, 'menuapp/index.html')


def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False
            user.save()
            PrivacyConsent.objects.create(
                user=user, policy_version=settings.PRIVACY_POLICY_VERSION,
                ip_address=request.META.get('REMOTE_ADDR') or None)

            code = EmailVerification.generate_code()
            EmailVerification.objects.create(user=user, code=code)

            try:
                send_mail(
                    _('Tu código de verificación - Mechanics'),
                    _('Hola %(username)s, tu código de verificación es: %(code)s') % {
                        'username': user.username, 'code': code,
                    },
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                logging.exception("Could not send the verification email to '%s'", user.email)
                # Remove the unverifiable account so the username and email can be reused
                user.delete()
                form.add_error(None, _("No se pudo enviar el correo de verificación. Inténtalo de nuevo más tarde."))
                return render(request, 'registration/signup.html', {'form': form})

            request.session.pop('email_change', None)
            request.session['verification_user_id'] = user.id
            return redirect('menuapp:verify_email')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


def privacy_view(request):
    """Privacy policy, with the controller's details taken from the settings."""
    return render(request, 'menuapp/privacy.html', {
        'policy_version': settings.PRIVACY_POLICY_VERSION,
        'legal_name': settings.LEGAL_NAME,
        'legal_id': settings.LEGAL_ID,
        'legal_address': settings.LEGAL_ADDRESS,
        'contact_email': settings.PRIVACY_CONTACT_EMAIL,
    })


def verify_email_view(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('menuapp:signup')

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

                        email_change = request.session.get('email_change')
                        if (email_change and email_change['user_id'] == user.id
                                and request.user.is_authenticated and request.user.id == user.id):
                            # Confirmed code for a new email address: apply it now
                            del request.session['email_change']
                            del request.session['verification_user_id']
                            new_email = email_change['email']
                            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                                messages.error(request, _("Este correo electrónico ya está en uso."))
                            else:
                                user.email = new_email
                                user.save(update_fields=['email'])
                                messages.success(request, _("Correo electrónico actualizado."))
                            return redirect('menuapp:profile')

                        if request.session.get('is_password_reset'):
                            # This is the recovery flow, we don't log in yet, we pass to change_psw
                            del request.session['is_password_reset']
                            del request.session['verification_user_id']
                            request.session['reset_user_id'] = user.id
                            return redirect('menuapp:change_psw')
                        else:
                            # This is the normal signup flow
                            login(request, user)
                            return redirect('menuapp:home')
                    else:
                        messages.error(request, _("El código ha expirado."))
                else:
                    messages.error(request, _("Código incorrecto."))
            except (User.DoesNotExist, EmailVerification.DoesNotExist):
                return redirect('menuapp:signup')
    else:
        form = VerificationForm()

    return render(request, 'registration/verify_email.html', {'form': form})


def recall_psw_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        print(f"Recovery attempt for email: '{email}'")
        
        # We use filter.first() to avoid MultipleObjectsReturned if there are duplicate emails
        user = User.objects.filter(email=email).first()
        
        if user:
            print(f"User found: {user.username} (ID: {user.id})")
            # We clear the previous code, since it's a OneToOneField (avoids IntegrityError)
            EmailVerification.objects.filter(user=user).delete()
            
            code = EmailVerification.generate_code()
            EmailVerification.objects.create(user=user, code=code)
            
            print(f"Code generated: {code} - Attempting to send email...")
            try:
                send_mail(
                    _('Recuperación de contraseña - Mechanics'),
                    _('Hola %(username)s, tu código para restablecer la contraseña es: %(code)s') % {
                        'username': user.username, 'code': code,
                    },
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                print("Email sent successfully.")
            except Exception as e:
                print(f"Critical error sending email: {e}")

            # We set in session that this user is going to reset their password
            request.session.pop('email_change', None)
            request.session['verification_user_id'] = user.id
            request.session['is_password_reset'] = True

            messages.success(request, _("Si el email ingresado corresponde a una cuenta registrada, se ha enviado un correo con instrucciones."))
            return redirect('menuapp:verify_email')
        else:
            print(f"No user found with email: '{email}'")
            return redirect('menuapp:login')
    
    return render(request, 'registration/recall_psw.html')

def change_psw_view(request):
    reset_user_id = request.session.get('reset_user_id')
    if request.user.is_authenticated:
        # Logged-in users change their password from the profile page (asks for the current one)
        return redirect('menuapp:profile')
    elif reset_user_id:
        try:
            target_user = User.objects.get(id=reset_user_id)
        except User.DoesNotExist:
            return redirect('menuapp:login')
    else:
        logging.warning("Attempt to access change_psw without authentication or recovery session.")
        return redirect('menuapp:login')

    if request.method == 'POST':
        form = SetPasswordForm(target_user, request.POST)
        if form.is_valid():
            form.save()
            if 'reset_user_id' in request.session:
                del request.session['reset_user_id']

            auth_user = authenticate(request, username=target_user.username, password=form.cleaned_data['new_password1'])
            if auth_user is not None:
                login(request, auth_user)
                return redirect('menuapp:home')

            return redirect('menuapp:login')
    else:
        form = SetPasswordForm(target_user)

    return render(request, 'registration/change_psw.html', {'form': form})


@login_required
def profile_view(request):
    """Personal data editor: name, username, email (confirmed with a code) and password."""
    user = request.user
    if is_demo(user):
        messages.info(request, _('La cuenta no está disponible en la demo.'))
        return redirect('menuapp:home')
    profile_form = ProfileForm(instance=user, initial={'email': user.email})
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        if request.POST.get('action') == 'password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, _("Contraseña cambiada con éxito."))
                return redirect('menuapp:profile')
        else:
            profile_form = ProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                new_email = profile_form.cleaned_data['email']
                profile_form.save()

                if new_email.lower() != (user.email or '').lower():
                    # The new address is applied only after the user confirms the code sent to it
                    EmailVerification.objects.filter(user=user).delete()
                    code = EmailVerification.generate_code()
                    EmailVerification.objects.create(user=user, code=code)
                    try:
                        send_mail(
                            _('Confirma tu nuevo correo - Mechanics'),
                            _('Hola %(username)s, tu código para confirmar el nuevo correo es: %(code)s') % {
                                'username': user.username, 'code': code,
                            },
                            settings.DEFAULT_FROM_EMAIL,
                            [new_email],
                            fail_silently=False,
                        )
                    except Exception:
                        logging.exception("Could not send the email-change code to '%s'", new_email)
                        messages.error(request, _("No se pudo enviar el correo de verificación. Inténtalo de nuevo más tarde."))
                        return redirect('menuapp:profile')
                    request.session['email_change'] = {'user_id': user.id, 'email': new_email}
                    request.session['verification_user_id'] = user.id
                    request.session.pop('is_password_reset', None)
                    return redirect('menuapp:verify_email')

                messages.success(request, _("Datos guardados."))
                return redirect('menuapp:profile')

    return render(request, 'registration/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


def logout_view(request):
    logging.info(f"User '{request.user.username}' has logged out.")
    from django.contrib.auth import logout
    logout(request)
    return redirect('menuapp:home')

def login_view(request):
    logging.info("Login attempt.")
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logging.info(f"User '{username}' logged in successfully.")
            return redirect('menuapp:home')
        else:
            messages.error(request, _("Credenciales incorrectas."))
    return render(request, 'registration/login.html')

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
