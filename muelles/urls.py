from django.urls import path
from django.views.generic import RedirectView
from muelles.views.calculadora_compresion import calculadora_compresion
from muelles.views.calculadora_traccion import calculadora_traccion
from muelles.views.calculadora_torsion import calculadora_torsion
from muelles.views.index import index
from muelles.views.calculate_blocking_length import calculate_blocking_length
from muelles.views.calculate_pitch import calculate_pitch

urlpatterns = [
    path('', index, name='muelles_index'),
    path('calculadora/compresion/', calculadora_compresion, name='muelles_calculadora_compresion'),
    path('calculadora/traccion/', calculadora_traccion, name='muelles_calculadora_traccion'),
    path('calculadora/torsion/', calculadora_torsion, name='muelles_calculadora_torsion'),
    path('api/calculate-blocking-length/', calculate_blocking_length, name='muelles_calculate_blocking_length'),
    path('api/calculate-pitch/', calculate_pitch, name='muelles_calculate_pitch'),
]