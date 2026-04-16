import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestMuellesPages:
    """
    Tests de carga para las páginas de la calculadora de muelles.
    """

    def test_muelles_index(self, client):
        url = reverse('muelles_index')
        response = client.get(url)
        assert response.status_code == 200

    def test_muelles_compresion_load(self, client):
        url = reverse('muelles_calculadora_compresion')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Muelle de Compresi" in response.content

    def test_muelles_traccion_load(self, client):
        url = reverse('muelles_calculadora_traccion')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Muelle de Tracci" in response.content

    def test_muelles_torsion_load(self, client):
        url = reverse('muelles_calculadora_torsion')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Muelle de Torsi" in response.content
