"""The Watergate Number entities."""

from collections.abc import Awaitable, Callable
import logging

from watergate_local_api import WatergateLocalApiClient

from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, UnitOfVolume
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    API,
    COORDINATOR,
    DOMAIN,
    SHUT_OFF_DURATION_ENTITY_NAME,
    SHUT_OFF_DURATION_SENSOR_NAME,
    SHUT_OFF_VOLUME_ENTITY_NAME,
    SHUT_OFF_VOLUME_SENSOR_NAME,
    SONIC_NAME,
)
from .coordinator import WatergateAgregatedRequests, WatergateDataCoordinator
from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all entries for Watergate Platform."""
    data_dict = hass.data[DOMAIN][config_entry.entry_id]
    api: WatergateLocalApiClient = data_dict[API]

    coordinator: WatergateDataCoordinator = data_dict[COORDINATOR]

    entities: list[NumberEntity] = [
        AutoShutOffNumberEntity(
            coordinator,
            config_entry,
            SHUT_OFF_VOLUME_ENTITY_NAME,
            SHUT_OFF_VOLUME_SENSOR_NAME,
            50,
            1000,
            UnitOfVolume.LITERS,
            lambda data: data.auto_shut_off_state.volume_threshold
            if data.auto_shut_off_state
            else None,
            lambda value: api.async_patch_auto_shut_off(volume=value),
        ),
        AutoShutOffNumberEntity(
            coordinator,
            config_entry,
            SHUT_OFF_DURATION_ENTITY_NAME,
            SHUT_OFF_DURATION_SENSOR_NAME,
            5,
            500,
            UnitOfTime.MINUTES,
            lambda data: data.auto_shut_off_state.duration_threshold
            if data.auto_shut_off_state
            else None,
            lambda value: api.async_patch_auto_shut_off(duration=value),
        ),
    ]

    for entity in entities:
        hass.data[DOMAIN][config_entry.entry_id][entity.unique_id] = entity

    async_add_entities(entities, True)


class AutoShutOffNumberEntity(
    CoordinatorEntity[WatergateDataCoordinator], NumberEntity
):
    """Define a Sonic Water Auto Shut Off Number entity."""

    def __init__(
        self,
        coordinator: WatergateDataCoordinator,
        entry: ConfigEntry,
        unique_id: str,
        name: str,
        min: int,
        max: int,
        unit: str,
        extractor: Callable[[WatergateAgregatedRequests], None],
        updater: Callable[[float], Awaitable[bool]],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.unique_id = f"{entry.data[SONIC_NAME]}.{unique_id}"
        self.name = name
        self._entry = entry
        self._extrafctor = extractor
        self._attr_native_value = self._extrafctor(coordinator.data)
        self._attr_native_min_value = min
        self._attr_native_max_value = max
        self._attr_native_unit_of_measurement = unit
        self._updater = updater

        self._attr_device_info = get_device_info(coordinator, entry)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._attr_native_value = self._extrafctor(self.coordinator.data)
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the diagnostic."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self._updater(value)
        self._attr_native_value = value
        self.async_write_ha_state()
