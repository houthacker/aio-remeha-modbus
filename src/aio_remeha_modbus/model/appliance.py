"""Provide a unified view of an appliance that is exposed in a ``Gateway``."""

from typing import Protocol


class CoolingSettings(Protocol):
    """Cooling settings at ``Appliance`` scope."""

    @property
    def forced_cooling_mode(self) -> bool:
        """Whether the appliance is in forced cooling mode.

        For appliances that don't support cooling, this is always `False`.
        """

    def is_cooling_required(self) -> bool:
        """Return whether the appliance requires cooling.

        Required cooling can be explicit (`forced_cooling_mode is True`) or implicit
        (the appliance is running in summer mode).
        """

    async def async_enable_forced_cooling_mode(self) -> None:
        """Put the appliance in forced cooling mode."""

    async def async_disable_forced_cooling_mode(self) -> None:
        """Get the appliance out of forced cooling mode.

        If forced cooling has been disabled, the appliance can still cool
        but it isn't forced to do so for supporting climate zones.

        However, the appliance might require a minimal (outside) temperature before
        zones are allowed to cool in this case.
        """


class Appliance(Protocol):
    """The main device that controls the available climate zones.

    Examples are a heat pump, condensing boiler, combi boiler or
    a furnace.
    """

    @property
    def cooling(self) -> CoolingSettings | None:
        """The cooling settings of this appliance.

        Returns:
            ``CoolingSettings | None``: The cooling settings, or `None` if the appliance
                does not support cooling.

        """
