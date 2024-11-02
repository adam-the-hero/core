"""The Watergate integration."""

from __future__ import annotations

import logging

from watergate_local_api import WatergateLocalApiClient
from watergate_local_api.models import WebhookEvent

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url

from .const import (
    API,
    COORDINATOR,
    DOMAIN,
    FLOW_ENTITY_NAME,
    GATEWAY_ENTITY_NAME,
    IP_ENTITY_NAME,
    POWER_SUPPLY_ENTITY_NAME,
    PRESSURE_ENTITY_NAME,
    RSSI_ENTITY_NAME,
    SHUT_OFF_EVENT_ENTITY_NAME,
    SONIC_ADDRESS,
    SONIC_NAME,
    SSID_ENTITY_NAME,
    SUBNET_ENTITY_NAME,
    TEMPERATURE_ENTITY_NAME,
    VALVE_ENTITY_NAME,
    WATER_FLOWING_ENTITY_NAME,
    WEBHOOK_ASO_REPORT_TYPE,
    WEBHOOK_POWER_SUPPLY_CHANGED_TYPE,
    WEBHOOK_TELEMETRY_TYPE,
    WEBHOOK_VALVE_TYPE,
    WEBHOOK_WIFI_CHANGED_TYPE,
)
from .coordinator import WatergateDataCoordinator

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.VALVE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Watergate from a config entry."""
    sonic_name = entry.data[SONIC_NAME]
    sonic_address = entry.data[SONIC_ADDRESS]

    _LOGGER.debug(
        "Setting up watergate local api integration for device: %s (IP: %s)",
        sonic_name,
        sonic_address,
    )

    webhook_id = entry.entry_id

    hass.components.webhook.async_register(
        DOMAIN, "Watergate", webhook_id, handle_webhook
    )

    watergate_client = WatergateLocalApiClient(sonic_address)

    _LOGGER.debug("Registered webhook: %s", webhook_id)

    coordinator = WatergateDataCoordinator(hass, watergate_client)

    await coordinator.async_refresh()

    instance_url = get_url(hass)

    await watergate_client.async_set_webhook_url(
        instance_url + "/api/webhook/" + webhook_id
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN][entry.entry_id][COORDINATOR] = coordinator
    hass.data[DOMAIN][entry.entry_id][API] = watergate_client
    hass.data[DOMAIN][entry.entry_id][SONIC_NAME] = sonic_name

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def handle_webhook(hass: HomeAssistant, webhook_id, request):
    """Handle incoming webhook request."""
    body = await request.json()

    _LOGGER.debug("Received webhook: %s", body)
    data = WebhookEvent.parse_webhook_event(body)

    body_type = body.get("type")
    data_dict = hass.data[DOMAIN][webhook_id]
    sonic_name = data_dict[SONIC_NAME]
    if body_type == WEBHOOK_TELEMETRY_TYPE:
        errors = data.errors or {}
        data_dict[f"{sonic_name}.{WATER_FLOWING_ENTITY_NAME}"].update(
            data.flow != 0 if "flow" not in errors else False,
        )
        data_dict[f"{sonic_name}.{FLOW_ENTITY_NAME}"].update(
            data.flow / 1000 if "flow" not in errors else None,
        )
        data_dict[f"{sonic_name}.{PRESSURE_ENTITY_NAME}"].update(
            data.pressure if "pressure" not in errors else None,
        )
        data_dict[f"{sonic_name}.{TEMPERATURE_ENTITY_NAME}"].update(
            data.temperature if "temperature" not in errors else None,
        )

    if body_type == WEBHOOK_VALVE_TYPE:
        data_dict[f"{sonic_name}.{VALVE_ENTITY_NAME}"].update(
            data.state,
        )

    if body_type == WEBHOOK_WIFI_CHANGED_TYPE:
        ip = data.ip
        data_dict[f"{sonic_name}.{IP_ENTITY_NAME}"].update(ip)
        data_dict[f"{sonic_name}.{GATEWAY_ENTITY_NAME}"].update(data.gateway)
        data_dict[f"{sonic_name}.{SUBNET_ENTITY_NAME}"].update(data.subnet)
        data_dict[f"{sonic_name}.{SSID_ENTITY_NAME}"].update(data.ssid)
        data_dict[f"{sonic_name}.{RSSI_ENTITY_NAME}"].update(data.rssi)

    if body_type == WEBHOOK_POWER_SUPPLY_CHANGED_TYPE:
        data_dict[f"{sonic_name}.{POWER_SUPPLY_ENTITY_NAME}"].update(data.supply)

    if body_type == WEBHOOK_ASO_REPORT_TYPE:
        data_dict[f"{sonic_name}.{SHUT_OFF_EVENT_ENTITY_NAME}"].update(data)
