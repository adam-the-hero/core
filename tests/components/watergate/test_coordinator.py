"""Tests for the Watergate coordinator."""

from unittest.mock import AsyncMock

import pytest
from watergate_local_api import WatergateApiException
from watergate_local_api.models import (
    AutoShutOffReport,
    AutoShutOffState,
    DeviceState,
    NetworkingData,
    TelemetryData,
)
from watergate_local_api.models.water_meter import WaterMeter

from homeassistant.components.watergate.coordinator import (
    WatergateAgregatedRequests,
    WatergateDataCoordinator,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.fixture
def mock_api_client():
    """Mock WatergateLocalApiClient."""
    client = AsyncMock()

    # Simulate successful responses for each API method
    client.async_get_device_state.return_value = DeviceState(
        valve_state="open",
        water_flow_indicator="on",
        mqtt_status="True",
        wifi_status="True",
        power_supply="battery",
        firmware_version="1.0.0",
        uptime=100,
        water_meter=WaterMeter(volume=1.2, duration=100),
    )
    client.async_get_telemetry_data.return_value = TelemetryData(
        flow=1.2, pressure=2, water_temperature=29.9, ongoing_event=None, errors=[]
    )
    client.async_get_networking.return_value = NetworkingData(
        mqtt_connected=True,
        wifi_connected=True,
        subnet="192.168.1.1/24",
        rssi=-50,
        wifi_uptime="1234",
        mqtt_uptime="1234",
        ip="192.168.1.10",
        gateway="192.168.1.1",
        ssid="test_network",
    )
    client.async_get_auto_shut_off.return_value = AutoShutOffState(
        enabled=True, volume_threshold=60, duration_threshold=60
    )
    client.async_get_auto_shut_off_report.return_value = AutoShutOffReport(
        type="VOLUME_THRESHOLD",
        timestamp="2024-10-30T10:00:00Z",
        volume=60,
        duration=60,
    )
    return client


@pytest.mark.asyncio
async def test_watergate_coordinator_successful_update(
    hass: HomeAssistant, mock_api_client
) -> None:
    """Test that the coordinator fetches data successfully."""
    # Initialize the coordinator with the mocked API client
    coordinator = WatergateDataCoordinator(hass, api=mock_api_client)

    # Run the _async_update_data method to fetch data
    data = await coordinator._async_update_data()

    # Verify the aggregated data
    assert isinstance(data, WatergateAgregatedRequests)
    assert data.state.valve_state == "open"
    assert data.telemetry.flow == 1.2
    assert data.networking.ip == "192.168.1.10"
    assert data.auto_shut_off_state.enabled is True
    assert data.auto_shut_off_report.timestamp == "2024-10-30T10:00:00Z"


@pytest.mark.asyncio
async def test_watergate_coordinator_api_failure(
    hass: HomeAssistant, mock_api_client
) -> None:
    """Test that the coordinator handles API failures correctly."""
    # Simulate an exception in one of the API calls
    mock_api_client.async_get_device_state.side_effect = WatergateApiException(
        "API error"
    )

    # Initialize the coordinator with the mocked API client
    coordinator = WatergateDataCoordinator(hass, api=mock_api_client)

    # Check that UpdateFailed is raised when an exception occurs
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
