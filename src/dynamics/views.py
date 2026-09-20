from django.shortcuts import render
from django.utils.translation import gettext as _

from dynamics.engine import ToggleSpring, simulate
from dynamics.forms import ToggleSpringForm
from dynamics.plots import render_force_curve_png


def index(request):
    result = None
    error = None

    if request.method == 'POST':
        form = ToggleSpringForm(request.POST)
        if form.is_valid():
            try:
                config = ToggleSpring(**form.cleaned_data)
                curve = simulate(config)
                result = {
                    'chart': render_force_curve_png(curve),
                    'preload_force': curve.preload_force,
                    'max_force': curve.max_force,
                    'dropoff_force': curve.dropoff_force,
                    'return_load': curve.return_load,
                    'hysteresis': curve.hysteresis,
                    'lever_ratio': curve.lever_ratio,
                    'total_travel_mm': curve.total_travel_mm,
                }
            except Exception as exc:
                error = _('Calculation error: %(error)s') % {'error': str(exc)}
    else:
        form = ToggleSpringForm()

    return render(request, 'dynamics/index.html', {
        'form': form,
        'result': result,
        'error': error,
    })
