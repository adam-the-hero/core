"""Implementation of the Watergate switch entity."""

import logging
from typing import Any

from watergate_local_api import WatergateLocalApiClient

from homeassistant.components.sensor import HomeAssistant
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    API,
    COORDINATOR,
    DOMAIN,
    SHUT_OFF_ENTITY_NAME,
    SHUT_OFF_SENSOR_NAME,
    SONIC_NAME,
)
from .coordinator import WatergateDataCoordinator
from .helpers import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all entries for Watergate Platform."""
    data_dict = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = data_dict[COORDINATOR]

    entities: list[SwitchEntity] = [
        AutoShutOffEntity(coordinator, config_entry, data_dict[API])
    ]

    for entity in entities:
        hass.data[DOMAIN][config_entry.entry_id][entity.unique_id] = entity

    async_add_entities(entities, True)


class AutoShutOffEntity(CoordinatorEntity[WatergateDataCoordinator], SwitchEntity):
    """Define a Sonic Water Auto Shut Off entity."""

    def __init__(
        self,
        coordinator: WatergateDataCoordinator,
        entry: ConfigEntry,
        api: WatergateLocalApiClient,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.unique_id = f"{entry.data[SONIC_NAME]}.{SHUT_OFF_ENTITY_NAME}"
        self.name = SHUT_OFF_SENSOR_NAME
        self._entry = entry
        self._attr_is_on = (
            coordinator.data.auto_shut_off_state.enabled
            if coordinator.data.auto_shut_off_state
            else False
        )
        self.icon = "mdi:water-pump"
        self._api_client = api

        self._attr_device_info = get_device_info(coordinator, entry)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._attr_is_on = (
            self.coordinator.data.auto_shut_off_state.enabled
            if self.coordinator.data.auto_shut_off_state
            else False
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._api_client.async_patch_auto_shut_off(enabled=True)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._api_client.async_patch_auto_shut_off(enabled=False)
        self._attr_is_on = False
        self.async_write_ha_state()
