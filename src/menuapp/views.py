from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from .forms import SignupForm, VerificationForm
from .models import EmailVerification
from django.contrib import messages

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False # El usuario no está activo hasta verificar email
            user.save()

            # Generar código de verificación
            code = EmailVerification.generate_code()
            EmailVerification.objects.create(user=user, code=code)

            # Enviar email
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
                        return redirect('index')
                    else:
                        messages.error(request, "El código ha expirado.")
                else:
                    messages.error(request, "Código incorrecto.")
            except (User.DoesNotExist, EmailVerification.DoesNotExist):
                return redirect('signup')
    else:
        form = VerificationForm()
    
    return render(request, 'registration/verify_email.html', {'form': form})
