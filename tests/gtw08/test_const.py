"""Tests for the GTW-08 constants."""

import pytest

from aio_remeha_modbus.gtw08.const import (
    PV_EFFICIENCY_TABLE,
    PV_MAX_TILT_DEGREES,
    PV_MIN_TILT_DEGREES,
    ClimateZoneScheduleId,
    Limits,
    PVSystemOrientation,
    SeasonalMode,
    Weekday,
)


@pytest.mark.parametrize(
    ("schedule_id", "expected"),
    [
        (ClimateZoneScheduleId.SCHEDULE_1, False),
        (ClimateZoneScheduleId.SCHEDULE_2, False),
        (ClimateZoneScheduleId.SCHEDULE_3, False),
        (ClimateZoneScheduleId.SCHEDULE_4, True),
    ],
)
def test_is_cooling_schedule(schedule_id: ClimateZoneScheduleId, expected: bool):
    """Test that only schedule 4 is a cooling schedule."""

    assert schedule_id.is_cooling_schedule() is expected


@pytest.mark.parametrize(
    "orientation",
    [
        pytest.param(
            orientation,
            marks=pytest.mark.xfail(
                orientation is PVSystemOrientation.EAST_WEST,
                strict=True,
                reason="EAST_WEST has no entry in PV_EFFICIENCY_TABLE.",
            ),
        )
        for orientation in PVSystemOrientation
    ],
)
def test_pv_efficiency_table_covers_all_orientations(orientation: PVSystemOrientation):
    """Test that every orientation has an efficiency for every tilt step."""

    tilts = list(range(PV_MIN_TILT_DEGREES, PV_MAX_TILT_DEGREES + 1, 10))

    assert orientation in PV_EFFICIENCY_TABLE
    assert sorted(PV_EFFICIENCY_TABLE[orientation]) == tilts


def test_pv_efficiency_table_values_are_ratios():
    """Test that all efficiencies are between 0 and 1."""

    for orientation, efficiencies in PV_EFFICIENCY_TABLE.items():
        for tilt, efficiency in efficiencies.items():
            assert 0 < efficiency <= 1, (orientation, tilt)


def test_limits_are_consistent():
    """Test that the minimum limits are lower than the maximum limits."""

    assert Limits.CH_MIN_TEMP < Limits.CH_MAX_TEMP
    assert Limits.DHW_MIN_TEMP < Limits.DHW_MAX_TEMP
    assert Limits.HYSTERESIS_MIN_TEMP < Limits.HYSTERESIS_MAX_TEMP


def test_weekday_matches_python_weekday():
    """Test that weekdays are numbered like `datetime.weekday()`."""

    assert [day.value for day in Weekday] == list(range(7))
    assert Weekday.MONDAY == 0
    assert Weekday.SUNDAY == 6


def test_seasonal_mode_values():
    """Test the raw values of the seasonal modes."""

    assert [mode.value for mode in SeasonalMode] == [0, 1, 2, 3]
