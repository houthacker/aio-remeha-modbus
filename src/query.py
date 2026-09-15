"""Helper script to retrieve modbus components via a cli."""

import argparse
import asyncio

from dateutil.tz import gettz, tzlocal
from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from aio_remeha_modbus.api.appliance import Appliance
from aio_remeha_modbus.api.climate_zone import ClimateZone
from aio_remeha_modbus.api.main_control_monitoring import MainControlMonitoring
from aio_remeha_modbus.api.system_discovery_table import SystemDiscoveryTable


async def main() -> int:  # noqa: D103
    parser = argparse.ArgumentParser(description="Query a device and print values.")
    add_connection_args(parser)

    parser.add_argument("--unit", type=int, default=100, help="Modbus unit id")
    parser.add_argument(
        "--timezone",
        type=str,
        default=tzlocal().tzname(dt=None),
        help="Time zone of your Remeha Appliance",
    )

    components = parser.add_argument_group(
        title="Components", description="The components you want to query"
    )
    components.add_argument(
        "--sd", action="store_true", default=True, help="The System Discovery Table (default)"
    )
    components.add_argument(
        "--mcm", action="store_true", default=False, help="The Main Control Monitoring"
    )
    components.add_argument(
        "--appliance",
        action="store_true",
        default=False,
        help="The Appliance. Also retrieved if zone >= 1",
    )
    components.add_argument(
        "--zone", type=int, default=0, help="A Climate Zone (one-based index, default=no zone)"
    )

    args = parser.parse_args()

    query_system_discovery: bool = args.sd
    query_main_control_monitoring: bool = args.mcm
    query_appliance: bool = args.appliance or args.zone >= 1
    query_zone: int = args.zone

    try:
        conn = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect: {err}")  # noqa: T201
        return 1

    print(f"Time zone: {args.timezone}")  # noqa: T201

    counting = CountingUnit(conn.for_unit(args.unit))
    try:
        if query_system_discovery:
            print("\n")  # noqa: T201
            discovery_table = SystemDiscoveryTable(unit=counting)
            await discovery_table.async_update()
            print_component(discovery_table)

        if query_main_control_monitoring:
            print("\n")  # noqa: T201
            main_control_monitoring = MainControlMonitoring(unit=counting)
            await main_control_monitoring.async_update()
            print_component(main_control_monitoring, title="Main Control Monitoring")

        if query_appliance:
            print("\n")  # noqa: T201
            appliance = Appliance(unit=counting)
            await appliance.async_update()
            print_component(appliance, title="Appliance")

        if query_zone >= 1:
            print("\n")  # noqa: T201
            zone = ClimateZone(
                unit=counting,
                sequence_id=query_zone,
                time_zone=gettz(args.timezone),
                appliance_requires_cooling=appliance.is_cooling_required(),
            )
            await zone.async_update()
            print_component(zone, title=f"Climate Zone {query_zone}")

    finally:
        await conn.close()

    print(f"\n{counting.reads} Modbus reads")  # noqa: T201
    return 0


raise SystemExit(asyncio.run(main()))
