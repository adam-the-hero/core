"""Common functions used in watergate integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, SONIC_NAME
from .coordinator import WatergateDataCoordinator


def extract_firmware_version(coordinator: WatergateDataCoordinator) -> str:
    """Extract firmware version from coordinator."""
    return coordinator.data.state.firmware_version if coordinator.data.state else ""


def get_device_info(
    coordinator: WatergateDataCoordinator, entry: ConfigEntry
) -> DeviceInfo:
    """Return device info for a Watergate device."""

    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data[SONIC_NAME],
        manufacturer=MANUFACTURER,
        sw_version=extract_firmware_version(coordinator),
    )
