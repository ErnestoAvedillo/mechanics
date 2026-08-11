
from django.shortcuts import render
from django.utils.translation import gettext as _


def index(request):
    """Main view of the springs application"""
    return render(request, 'muelles/index.html', {
        'titulo': _('Calculadora de Muelles'),
        'descripcion': _('Herramienta para calcular especificaciones de muelles')
    })

