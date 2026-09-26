"""Tests for time schedules."""

from datetime import date, time

import pytest

from aio_remeha_modbus.gtw08 import GTW08
from aio_remeha_modbus.gtw08.const import (
    BoilerConfiguration,
    BoilerEnergyLabel,
    PVSystem,
    PVSystemOrientation,
    UnitOfTemperature,
)
from aio_remeha_modbus.gtw08.schedule import (
    HourlyForecast,
    Timeslot,
    TimeslotActivity,
    TimeslotSetpointType,
    WeatherForecast,
    generate_dhw_day_schedule,
)
from tests.conftest import json_fixture


@pytest.mark.asyncio
async def test_generate_dhw_time_schedule(gtw_08: GTW08):
    """Test generating a time schedule for heating the DHW boiler."""

    weather_forecast: WeatherForecast = WeatherForecast(
        unit_of_temperature=UnitOfTemperature.CELSIUS,
        forecasts=[
            HourlyForecast.from_dict(native_forecast)
            for native_forecast in json_fixture("weather_forecast.json")
        ],
    )

    pv_system: PVSystem = PVSystem(
        nominal_power=5720,
        orientation=PVSystemOrientation.SOUTH,
        annual_efficiency_decrease=0.42,
        installation_date=date.today(),
        tilt=30.0,
    )

    boiler_config: BoilerConfiguration = BoilerConfiguration(
        volume=300, heat_loss_rate=None, energy_label=BoilerEnergyLabel.C
    )

    appliance = gtw_08.appliance
    zone = gtw_08.zones[1]
    assert zone is not None

    schedule = generate_dhw_day_schedule(
        weather_forecast=weather_forecast,
        pv_system=pv_system,
        boiler_config=boiler_config,
        calorifier_hysteresis=4.0,
        appliance_seasonal_mode=appliance.season_mode,
    )

    assert schedule == [
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("00:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.COMFORT,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("10:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("13:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.COMFORT,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("18:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("21:00"),
        ),
    ]


@pytest.mark.asyncio
async def test_generate_dhw_time_schedule_without_solar_yield(gtw_08: GTW08):
    """Test generating a time schedule for heating the DHW boiler on a day there is no solar yield."""

    weather_forecast: WeatherForecast = WeatherForecast(
        unit_of_temperature=UnitOfTemperature.CELSIUS,
        forecasts=[
            HourlyForecast.from_dict(native_forecast)
            for native_forecast in json_fixture("weather_forecast_no_sun.json")
        ],
    )

    pv_system: PVSystem = PVSystem(
        nominal_power=5720,
        orientation=PVSystemOrientation.SOUTH,
        annual_efficiency_decrease=0.42,
        installation_date=date.today(),
        tilt=30.0,
    )

    boiler_config: BoilerConfiguration = BoilerConfiguration(
        volume=300, heat_loss_rate=91.3, energy_label=None
    )

    appliance = gtw_08.appliance
    zone = gtw_08.zones[1]
    assert zone is not None

    schedule = generate_dhw_day_schedule(
        weather_forecast=weather_forecast,
        pv_system=pv_system,
        boiler_config=boiler_config,
        calorifier_hysteresis=4.0,
        appliance_seasonal_mode=appliance.season_mode,
    )

    assert schedule == [
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("00:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.COMFORT,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("10:00"),
        ),
        Timeslot(
            setpoint_type=TimeslotSetpointType.ECO,
            activity=TimeslotActivity.DHW,
            switch_time=time.fromisoformat("23:00"),
        ),
    ]
