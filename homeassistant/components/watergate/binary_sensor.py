"""The Watergate binary sensor integration."""

from collections.abc import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    COORDINATOR,
    DOMAIN,
    MQTT_CONNECTION_ENTITY_NAME,
    MQTT_CONNECTION_SENSOR_NAME,
    SONIC_NAME,
    WATER_FLOWING_ENTITY_NAME,
    WATER_FLOWING_SENSOR_NAME,
    WIFI_CONNECTION_ENTITY_NAME,
    WIFI_CONNECTION_SENSOR_NAME,
)
from .coordinator import WatergateAgregatedRequests, WatergateDataCoordinator
from .helpers import get_device_info


def water_flow_extractor(data: WatergateAgregatedRequests) -> bool:
    """Extract water flow indicator from data."""
    if data.state is not None and data.telemetry is not None:
        return (
            data.state.water_flow_indicator
            if "flow" not in data.telemetry.errors
            else False
        )
    return False


def mqttStatusExtractor(data: WatergateAgregatedRequests) -> bool:
    """Extract mqtt status from data."""
    if data.state is not None:
        return data.state.mqtt_status
    return False


def wifiStatusExtractor(data: WatergateAgregatedRequests) -> bool:
    """Extract wifi status from data."""
    if data.state is not None:
        return data.state.wifi_status
    return False


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all binary sensors for Watergate Platform."""

    data_dict = hass.data[DOMAIN][config_entry.entry_id]

    coordinator: WatergateDataCoordinator = data_dict[COORDINATOR]

    entities: list[SonicBinarySensor] = [
        SonicBinarySensor(
            coordinator,
            config_entry,
            WIFI_CONNECTION_SENSOR_NAME,
            WIFI_CONNECTION_ENTITY_NAME,
            None,
            wifiStatusExtractor,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicBinarySensor(
            coordinator,
            config_entry,
            MQTT_CONNECTION_SENSOR_NAME,
            MQTT_CONNECTION_ENTITY_NAME,
            None,
            mqttStatusExtractor,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicBinarySensor(
            coordinator,
            config_entry,
            WATER_FLOWING_SENSOR_NAME,
            WATER_FLOWING_ENTITY_NAME,
            BinarySensorDeviceClass.RUNNING,
            water_flow_extractor,
        ),
    ]

    for entity in entities:
        hass.data[DOMAIN][config_entry.entry_id][entity.unique_id] = entity

    async_add_entities(entities, True)


class SonicBinarySensor(
    CoordinatorEntity[WatergateDataCoordinator], BinarySensorEntity
):
    """Define a Sonic Binary Sensor entity."""

    _native_state: bool = False

    def __init__(
        self,
        coordinator: WatergateDataCoordinator,
        entry: ConfigEntry,
        name: str,
        unique_id: str,
        device_class: BinarySensorDeviceClass | None,
        extractor: Callable[[WatergateAgregatedRequests], bool],
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.unique_id = f"{entry.data[SONIC_NAME]}.{unique_id}"
        self.name = name
        self._entry = entry
        self.device_class = device_class
        self._extractor = extractor
        if entity_category is not None:
            self.entity_category = entity_category

        self._attr_device_info = get_device_info(coordinator, entry)
        self._native_state = self._extractor(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._native_state = self._extractor(self.coordinator.data)
        self.async_write_ha_state()

    def update(self, value: bool) -> None:
        """Update the sensor."""
        self._native_state = value
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return the diagnostic."""
        return self._native_state
