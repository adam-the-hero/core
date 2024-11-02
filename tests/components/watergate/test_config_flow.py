"""Tests for the Watergate config flow."""

from unittest.mock import patch

import pytest

from homeassistant import data_entry_flow
from homeassistant.components.watergate.config_flow import WatergateConfigFlow
from homeassistant.components.watergate.const import DOMAIN, SONIC_ADDRESS, SONIC_NAME
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME

from tests.common import HomeAssistant, MockConfigEntry


@pytest.mark.asyncio
async def test_step_user_form(hass: HomeAssistant) -> None:
    """Test displaying the initial form in the user step."""
    # Initialize the config flow
    flow = WatergateConfigFlow()
    flow.hass = hass

    # Start the user step without any input
    result = await flow.async_step_user(user_input=None)

    # Check that the form is returned with expected fields
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_NAME in result["data_schema"].schema
    assert CONF_IP_ADDRESS in result["data_schema"].schema


@pytest.mark.asyncio
async def test_step_user_create_entry(hass: HomeAssistant) -> None:
    """Test creating an entry from user input in the user step."""
    # Initialize the config flow
    flow = WatergateConfigFlow()
    flow.hass = hass

    # Define mock user input
    user_input = {
        CONF_NAME: "Test Device",
        CONF_IP_ADDRESS: "192.168.1.100",
    }

    # Run the user step with provided input
    result = await flow.async_step_user(user_input=user_input)

    # Check that an entry is created with the correct data
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Device"
    assert result["data"] == {
        SONIC_NAME: "Test Device",
        SONIC_ADDRESS: "192.168.1.100",
    }


@pytest.mark.asyncio
async def test_step_reconfigure_form(hass: HomeAssistant) -> None:
    """Test displaying the reconfigure form with default values."""
    # Initialize the config flow
    flow = WatergateConfigFlow()
    flow.hass = hass

    # Mock an existing ConfigEntry to use for reconfigure
    current_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Existing Device",
        data={
            SONIC_NAME: "Existing Device",
            SONIC_ADDRESS: "192.168.1.101",
        },
        source="user",
        entry_id="12345",
    )

    # Patch `_get_reconfigure_entry` to return the mock ConfigEntry
    with patch.object(flow, "_get_reconfigure_entry", return_value=current_entry):
        result = await flow.async_step_reconfigure(user_input=None)

    # Check that the form is returned with default values
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


@pytest.mark.asyncio
async def test_step_reconfigure_update_entry(hass: HomeAssistant) -> None:
    """Test updating an existing entry from reconfigure user input."""
    # Initialize the config flow
    flow = WatergateConfigFlow()
    flow.hass = hass

    # Mock an existing entry to use for reconfigure
    current_entry = {
        "entry_id": "12345",
        "data": {
            SONIC_NAME: "Existing Device",
            SONIC_ADDRESS: "192.168.1.101",
        },
    }

    # Define mock user input for updating
    new_user_input = {
        CONF_NAME: "Updated Device",
        CONF_IP_ADDRESS: "192.168.1.102",
    }

    # Patch `_get_reconfigure_entry` and `async_update_reload_and_abort`
    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=current_entry),
        patch.object(flow, "async_update_reload_and_abort") as mock_update_abort,
    ):
        await flow.async_step_reconfigure(user_input=new_user_input)

    mock_update_abort.assert_called_once_with(
        current_entry,
        data_updates={
            SONIC_NAME: "Updated Device",
            SONIC_ADDRESS: "192.168.1.102",
        },
    )
