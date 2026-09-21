"""Test that required files have been included in a build."""


def test_smoke():
    """Test that the API can be imported."""
    from aio_remeha_modbus.api import const  # noqa: PLC0415

    assert const.Limits.CH_MAX_TEMP is not None


if __name__ == "__main__":
    test_smoke()
