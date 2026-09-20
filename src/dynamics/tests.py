import pytest

from dynamics.engine import ToggleSpring, simulate


def _base_config(**overrides):
    defaults = dict(
        p_length=100.0, p_angle_deg=0.0,
        w_length=0.0, w_angle_deg=0.0, weight_force=0.0,
        t_length=50.0, t_angle_deg=90.0,
        u_length=50.0, u_angle_deg=90.0,
        spring_rate_1=0.0, free_length=0.0,
        total_travel_deg=30.0, steps=4,
    )
    defaults.update(overrides)
    return ToggleSpring(**defaults)


def test_degenerate_case_is_pure_weight_moment():
    """With every spring/friction/reaction term zeroed out, output force
    should reduce to the weight moment divided by the P arm — the simplest
    hand-checkable case, guarding against sign/geometry regressions."""
    config = _base_config(w_length=40.0, weight_force=5.0)
    result = simulate(config)

    import math
    for travel_mm, force in zip(result.travel_mm, result.force_forward):
        travel_rad = travel_mm / config.p_length
        expected = (
            -config.weight_force * config.w_length * math.cos(travel_rad)
        ) / config.p_length
        assert force == pytest.approx(expected, abs=1e-9)


def test_spring_moment_arm_sign_flips_across_toggle_point():
    """The toggle effect: as U rotates past T's angle, the pivot crosses
    the T-U line and the spring's moment arm (and thus its moment) flips
    sign."""
    config = _base_config(
        t_length=50.0, t_angle_deg=100.0,
        u_length=50.0, u_angle_deg=80.0,
        spring_rate_1=1.0, free_length=200.0,
        total_travel_deg=40.0, steps=20,
    )
    result = simulate(config)
    assert min(result.force_forward) < 0 < max(result.force_forward)
