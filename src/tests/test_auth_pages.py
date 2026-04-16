import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from menuapp.models import EmailVerification

@pytest.mark.django_db
class TestAuthFlow:
    """
    Tests para el flujo de Registro y Login.
    """

    def test_signup_page_load(self, client):
        url = reverse('signup')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Crear Cuenta" in response.content

    def test_signup_submission_creates_inactive_user(self, client):
        url = reverse('signup')
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }
        response = client.post(url, data)
        # Debería redirigir a la página de verificación
        assert response.status_code == 302
        assert response.url == reverse('verify_email')
        
        user = User.objects.get(username='testuser')
        assert user.is_active is False
        assert EmailVerification.objects.filter(user=user).exists()

    def test_verify_email_correct_code(self, client):
        user = User.objects.create_user(username='tester', email='t@e.com', password='p')
        user.is_active = False
        user.save()
        verification = EmailVerification.objects.create(user=user, code='123456')
        
        # Guardar el ID en la sesión
        session = client.session
        session['verification_user_id'] = user.id
        session.save()

        url = reverse('verify_email')
        response = client.post(url, {'code': '123456'})
        
        user.refresh_from_db()
        assert user.is_active is True
        assert response.status_code == 302

    def test_login_page_load(self, client):
        url = reverse('login')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Login" in response.content or b"Inicia" in response.content
