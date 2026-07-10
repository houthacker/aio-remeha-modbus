"""Test that required files have been included in a build."""


def test_smoke():
    """Test that the API can be imported."""
    from aio_remeha_modbus.api import const  # noqa: PLC0415

    assert const.MetaRegisters.NUMBER_OF_DEVICES.start_address == 128


if __name__ == "__main__":
    test_smoke()
