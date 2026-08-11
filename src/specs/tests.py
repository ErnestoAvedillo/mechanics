import os
import pytest
from django.contrib.auth.models import User
from specs.models import UserDocument
from pymongo import MongoClient

# Test data
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://mongodb:27017/')

@pytest.mark.django_db
class TestSpecsArchitecture:
    """
    Test suite to validate the integration of Users, Django and MongoDB.
    """

    def test_user_document_creation(self):
        # 1. Create the user in Django
        user = User.objects.create_user(username='test_engineer', password=os.environ.get('TEST_PASSWORD', 'test_pass_fallback'))
        
        # 2. Simulate a MongoDB ID
        simulated_mongo_id = "507f1f77bcf86cd799439011"
        
        # 3. Create the record in Django
        doc = UserDocument.objects.create(
            user=user,
            mongo_id=simulated_mongo_id,
            filename="ISO26262_Spec.pdf",
            company="VW"
        )
        
        # 4. Assertions
        assert UserDocument.objects.count() == 1
        assert doc.user.username == 'test_engineer'
        assert doc.company == "VW"
        print(f"\n✅ Document '{doc.filename}' correctly linked to user '{user.username}'.")

    def test_mongodb_connectivity(self):
        """
        Tests the real connection to the Docker MongoDB service.
        """
        try:
            client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
            db = client.test_database
            result = db.test_collection.insert_one({"test": "connection"})
            assert result.inserted_id is not None
            # Clean up
            db.test_collection.delete_one({"_id": result.inserted_id})
            print("\n✅ MongoDB connection established successfully.")
        except Exception as e:
            pytest.fail(f"MongoDB connection error: {e}")

    @pytest.mark.django_db
    def test_chat_query_endpoint(self):
        """
        Validates that the chat endpoint responds correctly (at least with a 400 error if there is no query).
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
        print("\n✅ Chat API validated successfully.")
