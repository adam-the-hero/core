"""Config flow for Watergate."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME

from .const import DOMAIN, SONIC_ADDRESS, SONIC_NAME

WATERGATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_IP_ADDRESS): str,
    }
)


class WatergateConfigFlow(ConfigFlow, domain=DOMAIN):
    """Watergate config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    SONIC_NAME: user_input[CONF_NAME],
                    SONIC_ADDRESS: user_input[CONF_IP_ADDRESS],
                },
            )

        return self.async_show_form(step_id="user", data_schema=WATERGATE_SCHEMA)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfigure dlow initiated by the user."""
        current_entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                current_entry,
                data_updates={
                    SONIC_NAME: user_input[CONF_NAME],
                    SONIC_ADDRESS: user_input[CONF_IP_ADDRESS],
                },
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=current_entry.data[SONIC_NAME]
                    ): str,
                    vol.Required(
                        CONF_IP_ADDRESS, default=current_entry.data[SONIC_ADDRESS]
                    ): str,
                }
            ),
        )
