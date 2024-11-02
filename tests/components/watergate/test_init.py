"""Tests for the Watergate integration init module."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.watergate import handle_webhook
from homeassistant.components.watergate.const import (
    API,
    COORDINATOR,
    DOMAIN,
    FLOW_ENTITY_NAME,
    PRESSURE_ENTITY_NAME,
    SONIC_NAME,
    TEMPERATURE_ENTITY_NAME,
    WATER_FLOWING_ENTITY_NAME,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        entry_id="1",
        domain=DOMAIN,
        data=MOCK_CONFIG,
    )


# Test the async setup of the config entry
async def test_async_setup_entry(hass: HomeAssistant, mock_entry) -> None:
    """Test setting up the Watergate integration."""
    hass.config.components.add("network")
    hass.config.internal_url = "http://hassio.local"
    mock_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.watergate.WatergateLocalApiClient"
        ) as mock_client,
        patch(
            "homeassistant.components.watergate.WatergateDataCoordinator"
        ) as mock_coordinator,
        patch(
            "homeassistant.helpers.network.get_url", return_value="http://hassio.local"
        ),
        patch("homeassistant.components.webhook.async_register") as mock_webhook,
    ):
        mock_coordinator_instance = mock_coordinator.return_value
        mock_coordinator_instance.async_refresh = AsyncMock(return_value=None)

        mock_client_instance = mock_client.return_value
        mock_client_instance.async_set_webhook_url = AsyncMock(return_value=None)

        # Use hass.config_entries.async_setup to load the entry
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()  # Wait for all setup tasks to complete

        # Check that the config entry is now in the LOADED state
        assert mock_entry.state == ConfigEntryState.LOADED

        # Check that the API client, webhook, and coordinator are set up
        mock_webhook.assert_called_once_with(
            hass,
            DOMAIN,
            "Watergate",
            mock_entry.entry_id,
            handle_webhook,
        )
        mock_client_instance.async_set_webhook_url.assert_called_once_with(
            "http://hassio.local/api/webhook/" + mock_entry.entry_id
        )
        assert hass.data[DOMAIN][mock_entry.entry_id][API] is mock_client_instance
        assert (
            hass.data[DOMAIN][mock_entry.entry_id][COORDINATOR]
            is mock_coordinator_instance
        )
        mock_coordinator_instance.async_refresh.assert_called_once()


async def test_handle_webhook(hass: HomeAssistant, mock_entry) -> None:
    """Test handling webhook events."""
    webhook_id = mock_entry.entry_id
    hass.config.components.add("network")
    hass.config.internal_url = "http://hassio.local"
    mock_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.watergate.WatergateLocalApiClient"
        ) as mock_client,
        patch(
            "homeassistant.components.watergate.WatergateDataCoordinator"
        ) as mock_coordinator,
        patch(
            "homeassistant.helpers.network.get_url", return_value="http://hassio.local"
        ),
        patch("homeassistant.components.webhook.async_register"),
    ):
        mock_coordinator_instance = mock_coordinator.return_value
        mock_coordinator_instance.async_refresh = AsyncMock(return_value=None)

        mock_client_instance = mock_client.return_value
        mock_client_instance.async_set_webhook_url = AsyncMock(return_value=None)

        # Use hass.config_entries.async_setup to load the entry
        await hass.config_entries.async_setup(mock_entry.entry_id)
        await hass.async_block_till_done()  # Wait for all setup tasks to complete

        # Mock different webhook data
        telemetry_data = {
            "type": "telemetry",
            "data": {"flow": 150, "pressure": 1015, "temperature": 20, "errors": []},
        }

        # Mock the state update method for entities
        mock_update = AsyncMock()
        hass.data[DOMAIN][webhook_id][
            f"{MOCK_CONFIG[SONIC_NAME]}.{WATER_FLOWING_ENTITY_NAME}"
        ].update = mock_update
        hass.data[DOMAIN][webhook_id][
            f"{MOCK_CONFIG[SONIC_NAME]}.{FLOW_ENTITY_NAME}"
        ].update = mock_update
        hass.data[DOMAIN][webhook_id][
            f"{MOCK_CONFIG[SONIC_NAME]}.{PRESSURE_ENTITY_NAME}"
        ].update = mock_update
        hass.data[DOMAIN][webhook_id][
            f"{MOCK_CONFIG[SONIC_NAME]}.{TEMPERATURE_ENTITY_NAME}"
        ].update = mock_update

        # Trigger webhook handler
        request = AsyncMock()
        request.json = AsyncMock(return_value=telemetry_data)
        await handle_webhook(hass, webhook_id, request)

        # Verify entity updates were called with correct data
        mock_update.assert_any_call(150 / 1000)  # Flow entity
        mock_update.assert_any_call(1015)  # Pressure entity
        mock_update.assert_any_call(20)  # Temperature entity
