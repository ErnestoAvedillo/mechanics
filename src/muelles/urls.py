from django.urls import path
from muelles.views.calculadora_compresion import (
    calculadora_compresion,
    calculadora_compresion_animacion,
    calculadora_compresion_pdf,
)
from muelles.views.calculadora_traccion import (
    calculadora_traccion,
    calculadora_traccion_animacion,
    calculadora_traccion_pdf,
)
from muelles.views.calculadora_torsion import (
    calculadora_torsion,
    calculadora_torsion_animacion,
    calculadora_torsion_pdf,
)
from muelles.views.calculadora_conico import (
    calculadora_conico,
    calculadora_conico_animacion,
    calculadora_conico_pdf,
)
from muelles.views.calculadora_conico_pitch_variable import (
    calculadora_conico_pitch_variable,
    calculadora_conico_pitch_variable_animacion,
    calculadora_conico_pitch_variable_pdf,
)
from muelles.views.calculadora_2k import (
    calculadora_2k,
    calculadora_2k_animacion,
    calculadora_2k_pdf,
)
from muelles.views.index import index
from muelles.views.calculate_blocking_length import calculate_blocking_length
from muelles.views.calculate_pitch import calculate_pitch

urlpatterns = [
    path('', index, name='muelles_index'),
    path('calculadora/compresion/', calculadora_compresion, name='muelles_calculadora_compresion'),
    path(
        'calculadora/compresion/pdf/', calculadora_compresion_pdf,
        name='muelles_calculadora_compresion_pdf',
    ),
    path(
        'calculadora/compresion/animacion/', calculadora_compresion_animacion,
        name='muelles_calculadora_compresion_animacion',
    ),
    path('calculadora/traccion/', calculadora_traccion, name='muelles_calculadora_traccion'),
    path(
        'calculadora/traccion/pdf/', calculadora_traccion_pdf,
        name='muelles_calculadora_traccion_pdf',
    ),
    path(
        'calculadora/traccion/animacion/', calculadora_traccion_animacion,
        name='muelles_calculadora_traccion_animacion',
    ),
    path('calculadora/torsion/', calculadora_torsion, name='muelles_calculadora_torsion'),
    path(
        'calculadora/torsion/pdf/', calculadora_torsion_pdf,
        name='muelles_calculadora_torsion_pdf',
    ),
    path(
        'calculadora/torsion/animacion/', calculadora_torsion_animacion,
        name='muelles_calculadora_torsion_animacion',
    ),
    path('calculadora/conico/', calculadora_conico, name='muelles_calculadora_conico'),
    path(
        'calculadora/conico/pdf/', calculadora_conico_pdf,
        name='muelles_calculadora_conico_pdf',
    ),
    path(
        'calculadora/conico/animacion/', calculadora_conico_animacion,
        name='muelles_calculadora_conico_animacion',
    ),
    path(
        'calculadora/conico-variable/', calculadora_conico_pitch_variable,
        name='muelles_calculadora_conico_pitch_variable',
    ),
    path(
        'calculadora/conico-variable/pdf/', calculadora_conico_pitch_variable_pdf,
        name='muelles_calculadora_conico_pitch_variable_pdf',
    ),
    path(
        'calculadora/conico-variable/animacion/', calculadora_conico_pitch_variable_animacion,
        name='muelles_calculadora_conico_pitch_variable_animacion',
    ),
    path('calculadora/2k/', calculadora_2k, name='muelles_calculadora_2k'),
    path(
        'calculadora/2k/pdf/', calculadora_2k_pdf,
        name='muelles_calculadora_2k_pdf',
    ),
    path(
        'calculadora/2k/animacion/', calculadora_2k_animacion,
        name='muelles_calculadora_2k_animacion',
    ),
    path('api/calculate-blocking-length/', calculate_blocking_length, name='muelles_calculate_blocking_length'),
    path('api/calculate-pitch/', calculate_pitch, name='muelles_calculate_pitch'),
]
