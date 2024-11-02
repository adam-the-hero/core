"""Support for Watergate Valve."""

from homeassistant.components.sensor import Any, HomeAssistant
from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    API,
    COORDINATOR,
    DOMAIN,
    SONIC_NAME,
    VALVE_ENTITY_NAME,
    VALVE_SENSOR_NAME,
)
from .coordinator import WatergateDataCoordinator
from .helpers import get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all entries for Wolf Platform."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    entities: list[SonicValve] = [SonicValve(hass, coordinator, config_entry)]

    async_add_entities(entities, True)


class SonicValve(CoordinatorEntity[WatergateDataCoordinator], ValveEntity):  # pylint: disable=hass-enforce-class-module
    """Define a Sonic Valve entity."""

    _attr_has_entity_name = True
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False
    _valve_state: str | None = None
    _attr_device_class = ValveDeviceClass.WATER

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: WatergateDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[SONIC_NAME]}.{VALVE_ENTITY_NAME}"
        self._entry = entry
        self._attr_name = VALVE_SENSOR_NAME

        self._attr_device_info = get_device_info(coordinator, entry)
        self._valve_state = (
            coordinator.data.state.valve_state if coordinator.data.state else None
        )
        hass.data[DOMAIN][entry.entry_id][self._attr_unique_id] = self
        self._api_client = hass.data[DOMAIN][entry.entry_id][API]

    @property
    def is_closed(self) -> bool:
        """Return if the valve is closed or not."""
        return self._valve_state == "closed"

    @property
    def is_opening(self) -> bool | None:
        """Return if the valve is opening or not."""
        return self._valve_state == "opening"

    @property
    def is_closing(self) -> bool | None:
        """Return if the valve is closing or not."""
        return self._valve_state == "closing"

    def update(self, valve_state: str) -> None:
        """Update the valve."""
        self._valve_state = valve_state
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._valve_state = (
            self.coordinator.data.state.valve_state
            if self.coordinator.data.state
            else None
        )
        self.async_write_ha_state()

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        await self._api_client.async_set_valve_state("open")
        self.update("opening")

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Open the valve."""
        await self._api_client.async_set_valve_state("close")
        self.update("closing")
