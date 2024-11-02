"""Support for Watergate sensors."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
import logging
from typing import Any

from watergate_local_api.models import AutoShutOffReport

from homeassistant.components.sensor import (
    HomeAssistant,
    SensorDeviceClass,
    SensorEntity,
    StateType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ASO_EVENT_DURATION_ATRIBUTE,
    ASO_EVENT_TYPE_ATRIBUTE,
    ASO_EVENT_VOLUME_ATRIBUTE,
    COORDINATOR,
    DOMAIN,
    FLOW_ENTITY_NAME,
    FLOW_SENSOR_NAME,
    GATEWAY_ENTITY_NAME,
    GATEWAY_SENSOR_NAME,
    IP_ENTITY_NAME,
    IP_SENSOR_NAME,
    MQTT_UPTIME_ENTITY_NAME,
    MQTT_UPTIME_SENSOR_NAME,
    POWER_SUPPLY_ENTITY_NAME,
    POWER_SUPPLY_SENSOR_NAME,
    PRESSURE_ENTITY_NAME,
    PRESSURE_SENSOR_NAME,
    RSSI_ENTITY_NAME,
    RSSI_SENSOR_NAME,
    SHUT_OFF_EVENT_ENTITY_NAME,
    SHUT_OFF_EVENT_SENSOR_NAME,
    SONIC_NAME,
    SSID_ENTITY_NAME,
    SSID_SENSOR_NAME,
    SUBNET_ENTITY_NAME,
    SUBNET_SENSOR_NAME,
    TEMPERATURE_ENTITY_NAME,
    TEMPERATURE_SENSOR_NAME,
    UPTIME_ENTITY_NAME,
    UPTIME_SENSOR_NAME,
    WATER_METER_DURATION_ENTITY_NAME,
    WATER_METER_DURATION_SENSOR_NAME,
    WATER_METER_VOLUME_ENTITY_NAME,
    WATER_METER_VOLUME_SENSOR_NAME,
    WIFI_UPTIME_ENTITY_NAME,
    WIFI_UPTIME_SENSOR_NAME,
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

    coordinator = data_dict[COORDINATOR]

    entities: list[SensorEntity] = [
        SonicSensor(
            coordinator,
            config_entry,
            WATER_METER_VOLUME_SENSOR_NAME,
            WATER_METER_VOLUME_ENTITY_NAME,
            UnitOfVolume.MILLILITERS,
            SensorDeviceClass.VOLUME,
            lambda data: data.state.water_meter.volume
            if data.state and data.state.water_meter
            else None,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            WATER_METER_DURATION_SENSOR_NAME,
            WATER_METER_DURATION_ENTITY_NAME,
            UnitOfTime.MILLISECONDS,
            SensorDeviceClass.DURATION,
            lambda data: data.state.water_meter.duration
            if data.state and data.state.water_meter
            else None,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            IP_SENSOR_NAME,
            IP_ENTITY_NAME,
            None,
            None,
            lambda data: data.networking.ip if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            GATEWAY_SENSOR_NAME,
            GATEWAY_ENTITY_NAME,
            None,
            None,
            lambda data: data.networking.gateway if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            SUBNET_SENSOR_NAME,
            SUBNET_ENTITY_NAME,
            None,
            None,
            lambda data: data.networking.subnet if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            SSID_SENSOR_NAME,
            SSID_ENTITY_NAME,
            None,
            None,
            lambda data: data.networking.ssid if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            RSSI_SENSOR_NAME,
            RSSI_ENTITY_NAME,
            SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            SensorDeviceClass.SIGNAL_STRENGTH,
            lambda data: data.networking.rssi if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            WIFI_UPTIME_SENSOR_NAME,
            WIFI_UPTIME_ENTITY_NAME,
            UnitOfTime.MILLISECONDS,
            SensorDeviceClass.DURATION,
            lambda data: data.networking.wifi_uptime if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            MQTT_UPTIME_SENSOR_NAME,
            MQTT_UPTIME_ENTITY_NAME,
            UnitOfTime.MILLISECONDS,
            SensorDeviceClass.DURATION,
            lambda data: data.networking.mqtt_uptime if data.networking else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            TEMPERATURE_SENSOR_NAME,
            TEMPERATURE_ENTITY_NAME,
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            lambda data: data.telemetry.water_temperature
            if data.telemetry and "temperature" not in data.telemetry.errors
            else None,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            PRESSURE_SENSOR_NAME,
            PRESSURE_ENTITY_NAME,
            UnitOfPressure.MBAR,
            SensorDeviceClass.PRESSURE,
            lambda data: data.telemetry.pressure
            if data.telemetry and "pressure" not in data.telemetry.errors
            else None,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            FLOW_SENSOR_NAME,
            FLOW_ENTITY_NAME,
            UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
            SensorDeviceClass.VOLUME_FLOW_RATE,
            lambda data: data.telemetry.flow / 1000
            if data.telemetry and "flow" not in data.telemetry.errors
            else None,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            UPTIME_SENSOR_NAME,
            UPTIME_ENTITY_NAME,
            UnitOfTime.MILLISECONDS,
            SensorDeviceClass.DURATION,
            lambda data: data.state.uptime if data.state else None,
            EntityCategory.DIAGNOSTIC,
        ),
        SonicSensor(
            coordinator,
            config_entry,
            POWER_SUPPLY_SENSOR_NAME,
            POWER_SUPPLY_ENTITY_NAME,
            None,
            None,
            lambda data: data.state.power_supply if data.state else None,
            EntityCategory.DIAGNOSTIC,
        ),
        AutoShutOffEventSensor(coordinator, config_entry),
    ]

    for entity in entities:
        hass.data[DOMAIN][config_entry.entry_id][entity.unique_id] = entity

    async_add_entities(entities, True)


class SonicSensor(CoordinatorEntity[WatergateDataCoordinator], SensorEntity):
    """Define a Sonic Valve entity."""

    _native_state: str | int | float | None = None

    def __init__(
        self,
        coordinator: WatergateDataCoordinator,
        entry: ConfigEntry,
        name: str,
        unique_id: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
        extractor: Callable[[WatergateAgregatedRequests], str | int | float | None],
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.unique_id = f"{entry.data[SONIC_NAME]}.{unique_id}"
        self.name = name
        self._entry = entry
        self._attr_native_unit_of_measurement = unit if unit else None
        self.device_class = device_class
        if entity_category:
            self.entity_category = entity_category
        self._extractor = extractor

        self._attr_device_info = get_device_info(coordinator, entry)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._native_state = self._extractor(self.coordinator.data)
        self.async_write_ha_state()

    def update(self, value: str | None) -> None:
        """Update the sensor."""
        self._native_state = value
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType:
        """Return the diagnostic."""
        return self._native_state


class AutoShutOffEventSensor(CoordinatorEntity[WatergateDataCoordinator], SensorEntity):
    """Representation of a sensor showing the latest long flow event."""

    _attributes: dict[str, str] = {}

    def __init__(
        self,
        coordinator: WatergateDataCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.unique_id = f"{entry.data[SONIC_NAME]}.{SHUT_OFF_EVENT_ENTITY_NAME}"
        self.name = SHUT_OFF_EVENT_SENSOR_NAME
        self._entry = entry
        self.device_class = SensorDeviceClass.TIMESTAMP
        self._attr_device_info = get_device_info(coordinator, entry)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return additional attributes."""
        return self._attributes

    def update(self, report: AutoShutOffReport) -> None:
        """Update the sensor."""
        self._attr_native_value = datetime.fromtimestamp(report.timestamp, UTC)
        self._attributes = {
            ASO_EVENT_TYPE_ATRIBUTE: report.type,
            ASO_EVENT_DURATION_ATRIBUTE: report.duration,
            ASO_EVENT_VOLUME_ATRIBUTE: report.volume,
        }
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        if self.coordinator.last_update_success:
            data = self.coordinator.data.auto_shut_off_report

            if data:
                self.update(data)
