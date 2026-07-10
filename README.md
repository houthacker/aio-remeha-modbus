# Async I/O  modbus API for Remeha appliances

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/dark_logo.png">
  <img alt="Remeha logo" src="./assets/logo.png">
</picture>

![GitHub License](https://img.shields.io/github/license/houthacker/aio-remeha-modbus)
[![ci](https://github.com/houthacker/aio-remeha-modbus/actions/workflows/ci.yaml/badge.svg)](https://github.com/houthacker/aio-remeha-modbus/actions/workflows/ci.yaml)
[![badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/houthacker/ab326b4825c5466a103921f42bf79ba9/raw/86a287f059442adaca5578e5c3a80b07239eb501/aio-remeha-modbus-cov-badge.json)](https://github.com/houthacker/aio-remeha-modbus/actions/workflows/coverage.yaml)

`aio-remeha-modbus` is an async python API for Remeha appliances.

## Installation
Add this library to your project from [PyPI](https://pypi.org) using
```bash
$ uv add aio-remeha-modbus>=0.1.0
```

or build it locally by checking out the source of this project and
```bash
$ uv build
...
$ uv pip install dist/*.whl
```

## Exposed API
The API is documented at [readthedocs](#). A short textual description of the most
important classes and their hierarchy is shown below.

#### Caching
All API calls are executed directly against the modbus proxy; no caching is implemented at this time.

#### Error handling
All errors raised by this library are intended to be translated.
To facilitate that, the base error class contains a `translation_key` field to look up the translation
and a `translation_placeholders` field. This is a `dict` to be used when extrapolating the error message.

### Configuration
To create a new api instance, you first need an instance of `api.config.Configuration`.
This can either be a `SerialConfiguration`, a `TcpConfiguration` or a `UdpConfiguration`,
depending on your needs.

### RemehaApi
To create a new API instance, call `api.api.RemehaApi.create()` and provide the `Configuration`
instance created previously.

### Appliance
The connected Remeha appliance can be retrieved using `RemehaApi.async_read_appliance()`.

### ClimateZone
Zones, as they are configured in the Remeha appliance are exposed as `ClimateZone` instances
and can be retrieved using `RemehaApi.async_read_zones()`, providing the corresponding `Appliance`.

### Zone schedules
When a `ClimateZone` is read from the appliance and its `mode` is `ClimateZoneMode.SCHEDULING`,
the schedules for each `Weekday` are available through `ClimateZone.current_schedule` as
instances of `api.schedule.ZoneSchedule`.