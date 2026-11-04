"""Tests for the Watergate siren platform."""

from copy import deepcopy
from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import (
    AsyncMock,
    MockConfigEntry,
    async_fire_time_changed,
    patch,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion
from watergate_local_api import WatergateApiException
from watergate_local_api.models import BuzzerSounds

from homeassistant.components.siren import (
    ATTR_AVAILABLE_TONES,
    ATTR_TONE,
    DOMAIN as SIREN_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from . import init_integration
from .const import DEFAULT_BUZZER_SOUNDS, DEFAULT_DEVICE_STATE_V3

ENTITY_ID = "siren.sonic_buzzer"


@pytest.mark.usefixtures("buzzer_device")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_entry: MockConfigEntry,
) -> None:
    """Test the siren entity and its registry entry."""
    with patch("homeassistant.components.watergate.PLATFORMS", [Platform.SIREN]):
        await init_integration(hass, mock_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_entry.entry_id)


@pytest.mark.usefixtures("mock_watergate_client")
async def test_no_siren_without_device_state_v3(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Firmware without device state v3 has no buzzer, so there is no siren."""
    await init_integration(hass, mock_entry)

    assert hass.states.get(ENTITY_ID) is None


async def test_no_siren_without_sounds(
    hass: HomeAssistant, buzzer_device: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    """A buzzer that lists no sounds cannot be started, so there is no siren."""
    buzzer_device.async_get_buzzer_sounds.return_value = BuzzerSounds(None)

    await init_integration(hass, mock_entry)

    assert hass.states.get(ENTITY_ID) is None


async def test_sounds_are_fetched_once(
    hass: HomeAssistant,
    buzzer_device: AsyncMock,
    mock_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The sound list is read at setup, not on every update."""
    await init_integration(hass, mock_entry)
    freezer.tick(timedelta(minutes=2, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert buzzer_device.async_get_device_state_v3.await_count == 2
    buzzer_device.async_get_buzzer_sounds.assert_awaited_once_with()


async def test_state_follows_buzzer_playing(
    hass: HomeAssistant, buzzer_device: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    """The siren is on while the device reports the buzzer playing."""
    playing = deepcopy(DEFAULT_DEVICE_STATE_V3)
    playing.buzzer_playing = True
    buzzer_device.async_get_device_state_v3.return_value = playing

    await init_integration(hass, mock_entry)

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_ON
    assert state.attributes[ATTR_AVAILABLE_TONES] == DEFAULT_BUZZER_SOUNDS


async def test_unavailable_without_buzzer_state(
    hass: HomeAssistant, buzzer_device: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    """A device state that does not report the buzzer leaves the siren unavailable."""
    unknown = deepcopy(DEFAULT_DEVICE_STATE_V3)
    unknown.buzzer_playing = None
    buzzer_device.async_get_device_state_v3.return_value = unknown

    await init_integration(hass, mock_entry)

    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("service_data", "expected_name"),
    [
        ({}, "beep"),
        ({ATTR_TONE: "christmas_2"}, "christmas_2"),
    ],
)
async def test_turn_on(
    hass: HomeAssistant,
    buzzer_device: AsyncMock,
    mock_entry: MockConfigEntry,
    service_data: dict[str, str],
    expected_name: str,
) -> None:
    """Turning the siren on starts a sound, the first one unless a tone is given."""
    await init_integration(hass, mock_entry)
    data_before = mock_entry.runtime_data.data
    buzzer_device.async_get_device_state_v3.reset_mock()

    await hass.services.async_call(
        SIREN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID, **service_data},
        blocking=True,
    )

    buzzer_device.async_control_buzzer.assert_awaited_once_with(
        "start", name=expected_name
    )
    # The state is not guessed: the device is asked again instead.
    buzzer_device.async_get_device_state_v3.assert_awaited_once_with()
    assert mock_entry.runtime_data.data is not data_before
    assert data_before.state.buzzer_playing is False


async def test_turn_on_state_comes_from_the_device(
    hass: HomeAssistant, buzzer_device: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    """The siren reports on only once the device says the buzzer is playing."""
    await init_integration(hass, mock_entry)
    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    playing = deepcopy(DEFAULT_DEVICE_STATE_V3)
    playing.buzzer_playing = True
    buzzer_device.async_get_device_state_v3.return_value = playing
    await hass.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )

    assert hass.states.get(ENTITY_ID).state == STATE_ON


async def test_turn_off(
    hass: HomeAssistant, buzzer_device: AsyncMock, mock_entry: MockConfigEntry
) -> None:
    """Turning the siren off stops the playback and refreshes the state."""
    await init_integration(hass, mock_entry)
    buzzer_device.async_get_device_state_v3.reset_mock()

    await hass.services.async_call(
        SIREN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )

    buzzer_device.async_control_buzzer.assert_awaited_once_with("stop", name=None)
    buzzer_device.async_get_device_state_v3.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("service", "service_data"),
    [(SERVICE_TURN_ON, {}), (SERVICE_TURN_OFF, {})],
)
async def test_failure_is_reported(
    hass: HomeAssistant,
    buzzer_device: AsyncMock,
    mock_entry: MockConfigEntry,
    service: str,
    service_data: dict[str, str],
) -> None:
    """A failed buzzer command surfaces as HomeAssistantError."""
    await init_integration(hass, mock_entry)
    buzzer_device.async_control_buzzer.side_effect = WatergateApiException("boom")
    buzzer_device.async_get_device_state_v3.reset_mock()

    with pytest.raises(HomeAssistantError, match="Failed to control the buzzer"):
        await hass.services.async_call(
            SIREN_DOMAIN,
            service,
            {ATTR_ENTITY_ID: ENTITY_ID, **service_data},
            blocking=True,
        )

    buzzer_device.async_get_device_state_v3.assert_not_awaited()
