import os
import pytest
from django.contrib.auth.models import User
from specs.models import UserDocument
from pymongo import MongoClient

# Datos de prueba
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://mongodb:27017/')

@pytest.mark.django_db
class TestSpecsArchitecture:
    """
    Test suite para validar la integración de Usuarios, Django y MongoDB.
    """

    def test_user_document_creation(self):
        # 1. Crear usuario en Django
        user = User.objects.create_user(username='test_engineer', password='password123')
        
        # 2. Simular un ID de MongoDB
        simulated_mongo_id = "507f1f77bcf86cd799439011"
        
        # 3. Crear registro en Django
        doc = UserDocument.objects.create(
            user=user,
            mongo_id=simulated_mongo_id,
            filename="ISO26262_Spec.pdf",
            company="VW"
        )
        
        # 4. Verificaciones
        assert UserDocument.objects.count() == 1
        assert doc.user.username == 'test_engineer'
        assert doc.company == "VW"
        print(f"\n✅ Documento '{doc.filename}' vinculado correctamente al usuario '{user.username}'.")

    def test_mongodb_connectivity(self):
        """
        Prueba la conexión real con el servicio MongoDB del Docker.
        """
        try:
            client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
            db = client.test_database
            result = db.test_collection.insert_one({"test": "connection"})
            assert result.inserted_id is not None
            # Limpiar
            db.test_collection.delete_one({"_id": result.inserted_id})
            print("\n✅ Conexión con MongoDB establecida correctamente.")
        except Exception as e:
            pytest.fail(f"Error de conexión con MongoDB: {e}")

    @pytest.mark.django_db
    def test_chat_query_endpoint(self):
        """
        Valida que el endpoint del chat responde correctamente (al menos con error 400 si no hay query).
        """
        from django.test import Client
        from django.urls import reverse
        
        c = Client()
        user = User.objects.create_user(username='tester', password='pass')
        c.login(username='tester', password='pass')
        
        url = reverse('specs:chat_query')
        response = c.post(url, {'query': ''})
        
        assert response.status_code == 400
        assert 'error' in response.json()
        print("\n✅ API del Chat validada correctamente.")
