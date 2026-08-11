from django.shortcuts import render
from django.utils.translation import gettext as _


def index(request):
    """Main view of the tolerances application"""
    return render(request, 'tolerances/index.html', {
        'titulo': _('Calculadora de Tolerancias'),
        'descripcion': _('Herramienta para calcular especificaciones de tolerancias')
    })

