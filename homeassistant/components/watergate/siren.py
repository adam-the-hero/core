"""Support for the Watergate buzzer."""

from typing import Any, override

from watergate_local_api import WatergateApiException

from homeassistant.components.siren import ATTR_TONE, SirenEntity, SirenEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import WatergateConfigEntry, WatergateDataCoordinator
from .entity import WatergateEntity

ENTITY_NAME = "buzzer"
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WatergateConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Watergate siren entity."""
    coordinator = config_entry.runtime_data
    # Only firmware reporting device state v3 has a buzzer, and a buzzer without a
    # sound to start cannot be used.
    if coordinator.supports_buzzer and coordinator.buzzer_sounds:
        async_add_entities([SonicBuzzer(coordinator, coordinator.buzzer_sounds)])


class SonicBuzzer(WatergateEntity, SirenEntity):
    """The buzzer of the Sonic."""

    _attr_translation_key = "buzzer"
    _attr_supported_features = (
        SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
        | SirenEntityFeature.TONES
    )

    def __init__(
        self, coordinator: WatergateDataCoordinator, sounds: list[str]
    ) -> None:
        """Initialize the siren."""
        super().__init__(coordinator, ENTITY_NAME)
        self._sounds = sounds
        self._attr_available_tones = list[int | str](sounds)

    @property
    @override
    def available(self) -> bool:
        """Return whether the device reports the buzzer state."""
        return (
            super().available and self.coordinator.data.state.buzzer_playing is not None
        )

    @property
    @override
    def is_on(self) -> bool | None:
        """Return whether the buzzer is playing."""
        return self.coordinator.data.state.buzzer_playing

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start playing a sound, the first available one unless a tone is given."""
        tone = str(kwargs.get(ATTR_TONE, self._sounds[0]))
        await self._async_control_buzzer("start", name=tone)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the playback."""
        await self._async_control_buzzer("stop")

    async def _async_control_buzzer(self, action: str, name: str | None = None) -> None:
        """Send a command to the buzzer and fetch the resulting state."""
        try:
            await self._api_client.async_control_buzzer(action, name=name)
        except WatergateApiException as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="buzzer_failed",
            ) from exc
        await self.coordinator.async_request_refresh()
