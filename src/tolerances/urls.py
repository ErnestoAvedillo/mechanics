from django.urls import path
from tolerances.views.index import index
from tolerances.views.pin_hole import pin_hole_calculator
from tolerances.views.pin_hole_pdf import pin_hole_pdf
from tolerances.views.pivot_bushing_hole import pivot_bushing_hole_calculator
from tolerances.views.pivot_bushing_hole_pdf import pivot_bushing_hole_pdf

urlpatterns = [
    path('', index, name='tolerances_index'),
    path('index/', index, name='tolerances_index_legacy'),
    path('pin-hole/', pin_hole_calculator, name='tolerances_pin_hole'),
    path('pin-hole/pdf/', pin_hole_pdf, name='tolerances_pin_hole_pdf'),
    path('pivot-bushing-hole/', pivot_bushing_hole_calculator, name='tolerances_pivot_bushing_hole'),
    path('pivot-bushing-hole/pdf/', pivot_bushing_hole_pdf, name='tolerances_pivot_bushing_hole_pdf'),
]