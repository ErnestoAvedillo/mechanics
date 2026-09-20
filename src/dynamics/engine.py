"""Pure calculation engine for the lever/toggle-spring force-vs-travel curve.

No Django imports here on purpose — this module is a straight port of the
physics from the reference spreadsheet's VBA macros, so it can be unit
tested and reasoned about independently of the web layer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def _cartesian(length: float, angle_rad: float) -> tuple[float, float]:
    return length * math.cos(angle_rad), length * math.sin(angle_rad)


def _spring_force(
    length: float,
    free_length: float,
    rate_1: float,
    rate_2: float,
    rate_3: float,
    block_length_1: float,
    block_length_2: float,
) -> float:
    """Three-stage piecewise-linear spring force, staged by current length."""
    if length >= block_length_1:
        return rate_1 * (free_length - length)
    stage_1 = rate_1 * (free_length - block_length_1)
    if length >= block_length_2:
        return rate_2 * (block_length_1 - length) + stage_1
    stage_2 = rate_2 * (block_length_1 - block_length_2) + stage_1
    return rate_3 * (block_length_2 - length) + stage_2


@dataclass
class ToggleSpring:
    """Full input configuration for one force-curve simulation run."""

    # Pivot -> force application point (the lever's output end)
    p_length: float
    p_angle_deg: float

    # Pivot -> weight center of the lever
    w_length: float
    w_angle_deg: float
    weight_force: float

    # Toggle spring anchor points: T is fixed to the frame, U rotates with
    # the lever. The spring's moment arm about the pivot changes sign when
    # the pivot crosses the T-U line — that sign flip is the toggle effect.
    t_length: float
    t_angle_deg: float
    u_length: float
    u_angle_deg: float
    spring_rate_1: float
    free_length: float
    spring_rate_2: float = 0.0
    spring_rate_3: float = 0.0
    block_length_1: float = -1e9
    block_length_2: float = -1e9

    # Friction (acts at the same arm as the output force) and damping
    # (acts at its own arm), both direction-dependent (forward vs. return).
    friction_force: float = 0.0
    damping_force: float = 0.0
    damping_arm: float = 0.0

    # Reaction load, simplified as a linear spring acting on the lever's
    # own linear travel (a simplification of the detailed reaction-load
    # geometry in the reference model, deferred to a later phase).
    reaction_rate: float = 0.0
    reaction_preload: float = 0.0
    reaction_arm: float = 0.0

    total_travel_deg: float = 0.0
    steps: int = 20

    @property
    def total_travel_rad(self) -> float:
        return math.radians(self.total_travel_deg)


@dataclass
class ToggleSpringResult:
    travel_mm: list[float]
    force_forward: list[float]
    force_return: list[float]
    preload_force: float
    max_force: float
    dropoff_force: float
    return_load: float
    hysteresis: float
    lever_ratio: float
    total_travel_mm: float


def _moment_at(config: ToggleSpring, travel_rad: float, direction_sign: int) -> float:
    t_angle = math.radians(config.t_angle_deg)
    u_angle = math.radians(config.u_angle_deg) + travel_rad
    w_angle = math.radians(config.w_angle_deg) + travel_rad

    tx, ty = _cartesian(config.t_length, t_angle)
    ux, uy = _cartesian(config.u_length, u_angle)

    weight_moment = -config.weight_force * config.w_length * math.cos(w_angle)

    spring_length = math.hypot(tx - ux, ty - uy)
    spring_force = _spring_force(
        spring_length,
        config.free_length,
        config.spring_rate_1,
        config.spring_rate_2,
        config.spring_rate_3,
        config.block_length_1,
        config.block_length_2,
    )
    dx, dy = tx - ux, ty - uy
    line_len = math.hypot(dx, dy)
    spring_arm = ((0 - ux) * dy - (0 - uy) * dx) / line_len if line_len else 0.0
    spring_moment = spring_force * spring_arm

    reaction_travel_mm = config.p_length * travel_rad
    reaction_force = max(
        0.0, config.reaction_rate * reaction_travel_mm + config.reaction_preload
    )
    reaction_moment = reaction_force * config.reaction_arm

    friction_moment = direction_sign * (
        config.friction_force * config.p_length
        + config.damping_force * config.damping_arm
    )

    return weight_moment + spring_moment + reaction_moment + friction_moment


def simulate(config: ToggleSpring) -> ToggleSpringResult:
    n_points = config.steps + 2
    step_rad = config.total_travel_rad / (config.steps + 1) if config.steps else 0.0

    travel_mm: list[float] = []
    force_forward: list[float] = []
    force_return: list[float] = []

    for i in range(n_points):
        travel_rad = step_rad * i
        travel_mm.append(config.p_length * travel_rad)
        force_forward.append(_moment_at(config, travel_rad, 1) / config.p_length)
        force_return.append(_moment_at(config, travel_rad, -1) / config.p_length)

    peak_index = max(range(len(force_forward)), key=force_forward.__getitem__)
    dropoff_force = (
        force_forward[peak_index + 1]
        if peak_index + 1 < len(force_forward)
        else force_forward[peak_index]
    )

    preload_force = force_forward[0]
    return_load = force_return[0]

    return ToggleSpringResult(
        travel_mm=travel_mm,
        force_forward=force_forward,
        force_return=force_return,
        preload_force=preload_force,
        max_force=max(force_forward),
        dropoff_force=dropoff_force,
        return_load=return_load,
        hysteresis=abs(preload_force - return_load),
        lever_ratio=(config.p_length / config.reaction_arm) if config.reaction_arm else 0.0,
        total_travel_mm=travel_mm[-1] if travel_mm else 0.0,
    )
