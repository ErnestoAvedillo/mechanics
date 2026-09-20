"""Chart rendering for the toggle-spring force curve, base64 PNG."""
import base64
import io

import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt

from dynamics.engine import ToggleSpringResult


def render_force_curve_png(result: ToggleSpringResult) -> str:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(result.travel_mm, result.force_forward, label='Forward', color='#2563eb')
    ax.plot(result.travel_mm, result.force_return, label='Return', color='#dc2626')
    ax.set_xlabel('Travel [mm]')
    ax.set_ylabel('Output force [N]')
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=110)
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()
