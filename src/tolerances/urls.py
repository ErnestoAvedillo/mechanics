from django.urls import path
from tolerances.views.index import index
from tolerances.views.pin_hole import pin_hole_calculator
from tolerances.views.pin_hole_pdf import pin_hole_pdf
from tolerances.views.pivot_bushing_hole_radial import pivot_bushing_hole_radial_calculator
from tolerances.views.pivot_bushing_hole_radial_pdf import pivot_bushing_hole_radial_pdf
from tolerances.views.pivot_bushing_hole_axial import pivot_bushing_hole_axial_calculator
from tolerances.views.pivot_bushing_hole_axial_pdf import pivot_bushing_hole_axial_pdf
from tolerances.views.insert_support import insert_support_calculator
from tolerances.views.insert_support_pdf import insert_support_pdf
urlpatterns = [
    path('', index, name='tolerances_index'),
    path('index/', index, name='tolerances_index_legacy'),
    path('pin-hole/', pin_hole_calculator, name='tolerances_pin_hole'),
    path('pin-hole/pdf/', pin_hole_pdf, name='tolerances_pin_hole_pdf'),
    path('pivot-bushing-hole-axial/', pivot_bushing_hole_axial_calculator, name='tolerances_pivot_bushing_hole_axial'),
    path('pivot-bushing-hole-radial/', pivot_bushing_hole_radial_calculator, name='tolerances_pivot_bushing_hole_radial'),
    path('pivot-bushing-hole-radial/pdf/', pivot_bushing_hole_radial_pdf, name='tolerances_pivot_bushing_hole_radial_pdf'),
    path('pivot-bushing-hole-axial/pdf/', pivot_bushing_hole_axial_pdf, name='tolerances_pivot_bushing_hole_axial_pdf'),
    path('insert-support/', insert_support_calculator, name='tolerances_insert_support'),
    path('insert-support/pdf/', insert_support_pdf, name='tolerances_insert_support_pdf'),
    ]
