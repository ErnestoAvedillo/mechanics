from django.shortcuts import render


def index(request):
    """Vista principal de la aplicación de tolerancias"""
    return render(request, 'tolerances/index.html', {
        'titulo': 'Calculadora de Tolerancias',
        'descripcion': 'Herramienta para calcular especificaciones de tolerancias'
    })

