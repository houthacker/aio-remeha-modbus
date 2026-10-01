"""A unified ``Protocol`` for climate zones."""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClimateZone(Protocol):
    """A separate heating- or climate circuit that can be monitored and controlled independently."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether this circuit is enabled in the related appliance."""

    @property
    @abstractmethod
    def id(self) -> int:
        """The one-based sequence id of this circuit."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A short name of this circuit.

        Examples are `CIRCA`, `DHW` or `A`.
        """

    @property
    @abstractmethod
    def current_temperature(self) -> float:
        """The current temperature in °C.

        The actual temperature source depends on the type of zone. For example,
        a central heating (CH) circuit returns the room temperature while a domestic
        hot water (DHW) circuit returns the tank temperature.
        """

    @property
    @abstractmethod
    def current_setpoint(self) -> float | None:
        """The current setpoint in °C.

        Returns:
          `float | None` The current zone setpoint, or `None` if this zone does not support a current setpoint.

        """

    @abstractmethod
    async def async_set_current_setpoint(self, setpoint: float) -> None:
        """Set the current setpoint for this zone.

        Args:
            setpoint (float): The target temperature in °C.

        """
