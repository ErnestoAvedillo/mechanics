
from django.shortcuts import render


def index(request):
    """Vista principal de la aplicación de muelles"""
    return render(request, 'muelles/index.html', {
        'titulo': 'Calculadora de Muelles',
        'descripcion': 'Herramienta para calcular especificaciones de muelles'
    })

