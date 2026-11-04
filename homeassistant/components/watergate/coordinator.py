"""Coordinator for Watergate API."""

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, override

from watergate_local_api import WatergateApiException, WatergateLocalApiClient
from watergate_local_api.models import (
    AutoShutOffState,
    DeviceState,
    DeviceStateV2,
    DeviceStateV3,
    NetworkingData,
    TelemetryData,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _as_device_state_v3(
    state: DeviceState | DeviceStateV2 | None,
) -> DeviceStateV3 | None:
    """Present an older device state as v3.

    Firmware without device state v2 reports a single water meter holding the difference
    between the positive and negative readings, so it is surfaced as the positive one and
    the negative one is left unset. Firmware without device state v3 has no buzzer, so
    its playing state is left unset.
    """
    if state is None or isinstance(state, DeviceStateV3):
        return state
    if isinstance(state, DeviceStateV2):
        water_meter_positive = state.water_meter_positive
        water_meter_negative = state.water_meter_negative
    else:
        water_meter_positive = state.water_meter
        water_meter_negative = None
    return DeviceStateV3(
        valve_state=state.valve_state,
        water_flow_indicator=state.water_flow_indicator,
        mqtt_status=state.mqtt_status,
        wifi_status=state.wifi_status,
        power_supply=state.power_supply,
        firmware_version=state.firmware_version,
        uptime=state.uptime,
        water_meter_positive=water_meter_positive,
        water_meter_negative=water_meter_negative,
        serial_number=state.serial_number,
        buzzer_playing=None,
    )


@dataclass
class WatergateAgregatedRequests:
    """Class to hold aggregated requests."""

    state: DeviceStateV3
    telemetry: TelemetryData
    networking: NetworkingData
    auto_shut_off: AutoShutOffState


type WatergateConfigEntry = ConfigEntry[WatergateDataCoordinator]


class WatergateDataCoordinator(DataUpdateCoordinator[WatergateAgregatedRequests]):
    """Class to manage fetching watergate data."""

    config_entry: WatergateConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: WatergateConfigEntry,
        api: WatergateLocalApiClient,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=2),
        )
        self.api = api
        # The newest device state version the firmware is not yet known to lack, and
        # whether that version has been read successfully.
        self._state_version = 3
        self._state_version_confirmed = False
        self.buzzer_sounds: list[str] | None = None

    @property
    def supports_buzzer(self) -> bool:
        """Return whether the firmware reports device state v3, i.e. has a buzzer."""
        return self._state_version == 3

    @override
    async def _async_update_data(self) -> WatergateAgregatedRequests:
        try:
            state = await self._async_fetch_device_state()
            if self.supports_buzzer and self.buzzer_sounds is None:
                # The supported sounds are fixed by the firmware, so they are read once.
                sounds = await self.api.async_get_buzzer_sounds()
                self.buzzer_sounds = (sounds.sounds if sounds else None) or []
            telemetry = await self.api.async_get_telemetry_data()
            networking = await self.api.async_get_networking()
            auto_shut_off = await self.api.async_get_auto_shut_off()
        except WatergateApiException as exc:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="device_unavailable",
            ) from exc
        if TYPE_CHECKING:
            # Every supported Sonic firmware reports auto shut-off; the client
            # raises rather than returning None when the read genuinely fails.
            assert auto_shut_off is not None
        return WatergateAgregatedRequests(state, telemetry, networking, auto_shut_off)

    async def _async_read_device_state(self, version: int) -> DeviceStateV3 | None:
        """Read the device state in the given version, presented as v3."""
        if version == 3:
            return await self.api.async_get_device_state_v3()
        if version == 2:
            return _as_device_state_v3(await self.api.async_get_device_state_v2())
        return _as_device_state_v3(await self.api.async_get_device_state())

    async def _async_fetch_device_state(self) -> DeviceStateV3 | None:
        """Fetch the device state, preferring v3 and falling back to v2, then v1."""
        version = self._state_version
        try:
            state = await self._async_read_device_state(version)
        except WatergateApiException:
            if version == 1 or self._state_version_confirmed:
                # The version has been read before (or is the oldest), so this is a
                # transient failure, not old firmware: keep the last data rather than
                # switching the meter source.
                raise
            # The client reports a rejected media type and an unreachable device the same
            # way, so only a successful v1 read proves the firmware simply lacks the newer
            # versions. The device may have come back in between, so they are tried once
            # more before the downgrade is made permanent.
            state_v1 = await self._async_read_device_state(1)
            for candidate in range(version, 1, -1):
                try:
                    state = await self._async_read_device_state(candidate)
                except WatergateApiException:
                    continue
                self._state_version = candidate
                self._state_version_confirmed = True
                return state
            self._state_version = 1
            _LOGGER.debug("Device state v2 is not supported, falling back to v1")
            return state_v1
        self._state_version_confirmed = True
        return state

    @override
    def async_set_updated_data(self, data: WatergateAgregatedRequests) -> None:
        """Manually update data, notify listeners and DO NOT reset refresh interval."""

        self.data = data
        self.logger.debug(
            "Manually updated %s data",
            self.name,
        )

        self.async_update_listeners()
