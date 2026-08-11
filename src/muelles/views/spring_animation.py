"""Generates 3D GIF animations of a spring's geometry from an already
calculated springcalc object.

The spring's behavior is not animated with physical accuracy (coil
collisions, non-linearities near the solid length, etc.): the goal is to
give a clear visual representation of the movement between two load
positions (or two angles, in the case of torsion).
"""
import tempfile

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from django.http import HttpResponse
from matplotlib.animation import FuncAnimation, PillowWriter
from springcalc import ureg
matplotlib.use('Agg')

NUM_FRAMES = 18
NUM_POINTS = 150


def _to_mm(value):
    return float(value.to('mm').magnitude) if hasattr(value, 'magnitude') else float(value)


def _base_helix(muelle, num_points=NUM_POINTS):
    """Centerline (thetas, zs, radii in mm) of the spring in its free state."""
    if hasattr(muelle, 'get_h_theta_development'):
        thetas, zs_full = muelle.get_h_theta_development(num_points)
        zs_full = np.array([_to_mm(z) for z in zs_full])
        radii = np.array([
            _to_mm(muelle.f_mean_diameter(z * ureg.mm)) / 2.0 for z in zs_full
        ])
    else:
        theta_max = 2 * np.pi * float(muelle.nr_coils)
        thetas = np.linspace(0, theta_max, num_points)
        radius_const = _to_mm(muelle.mean_diameter) / 2.0
        pitch_mm = _to_mm(muelle.pitch)
        zs_full = pitch_mm * thetas / (2 * np.pi)
        radii = np.full_like(thetas, radius_const)
    return thetas, zs_full, radii


def _compression_frames(muelle, length_start_mm, length_end_mm, num_frames=NUM_FRAMES, num_points=NUM_POINTS):
    thetas, zs_full, radii = _base_helix(muelle, num_points)
    free_length_mm = zs_full[-1] if zs_full[-1] else _to_mm(muelle.free_length)
    xs = radii * np.cos(thetas)
    ys = radii * np.sin(thetas)
    frames = []
    for t in np.linspace(0, 1, num_frames):
        length_t = length_start_mm + (length_end_mm - length_start_mm) * t
        scale = length_t / free_length_mm if free_length_mm else 1.0
        frames.append((xs, ys, zs_full * scale))
    return frames


def _twist_frames(muelle, angle_start_deg, angle_end_deg, num_frames=NUM_FRAMES, num_points=NUM_POINTS):
    """Simulates the relative rotation between legs: the base (z=0) stays
    fixed and the rotation is applied increasingly with height."""
    thetas, zs_full, radii = _base_helix(muelle, num_points)
    free_length_mm = zs_full[-1] if zs_full[-1] else 1.0
    height_fraction = zs_full / free_length_mm if free_length_mm else zs_full
    frames = []
    for t in np.linspace(0, 1, num_frames):
        angle_t = angle_start_deg + (angle_end_deg - angle_start_deg) * t
        phi = thetas + np.radians(angle_t) * height_fraction
        frames.append((radii * np.cos(phi), radii * np.sin(phi), zs_full))
    return frames


def _render_gif_bytes(frames):
    all_x = np.concatenate([f[0] for f in frames])
    all_y = np.concatenate([f[1] for f in frames])
    all_z = np.concatenate([f[2] for f in frames])

    fig = plt.figure(figsize=(4.2, 4.2), dpi=90)
    ax = fig.add_subplot(projection='3d')
    line, = ax.plot([], [], [], linewidth=2)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    ax.set_title('Spring animation')
    ax.set_xlim(all_x.min(), all_x.max())
    ax.set_ylim(all_y.min(), all_y.max())
    ax.set_zlim(all_z.min(), all_z.max())
    ax.set_box_aspect((np.ptp(all_x) or 1.0, np.ptp(all_y) or 1.0, np.ptp(all_z) or 1.0))
    ax.set_proj_type('ortho')
    ax.view_init(elev=20, azim=45)

    def update(i):
        xs, ys, zs = frames[i]
        line.set_data(xs, ys)
        line.set_3d_properties(zs)
        return (line,)

    anim = FuncAnimation(fig, update, frames=len(frames), interval=90, blit=False)
    with tempfile.NamedTemporaryFile(suffix='.gif') as tmp_file:
        anim.save(tmp_file.name, writer=PillowWriter(fps=11))
        plt.close(fig)
        tmp_file.seek(0)
        return tmp_file.read()


def _ping_pong(frames):
    return frames + frames[::-1][1:-1]


def build_compression_animation_gif(muelle, length_start_mm, length_end_mm):
    """GIF (bytes) of the spring moving between two lengths."""
    frames = _ping_pong(_compression_frames(muelle, length_start_mm, length_end_mm))
    return _render_gif_bytes(frames)


def build_twist_animation_gif(muelle, angle_start_deg, angle_end_deg):
    """GIF (bytes) of the torsion spring rotating between two angles."""
    frames = _ping_pong(_twist_frames(muelle, angle_start_deg, angle_end_deg))
    return _render_gif_bytes(frames)


def animation_http_response(gif_bytes, filename):
    response = HttpResponse(gif_bytes, content_type='image/gif')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
