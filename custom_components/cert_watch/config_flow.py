from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SNI,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
)


class CertWatchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Optional(CONF_SNI, default=""): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL_HOURS, default=DEFAULT_SCAN_INTERVAL_HOURS
                    ): vol.Coerce(int),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        host = user_input[CONF_HOST].strip()
        port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
        sni = (user_input.get(CONF_SNI) or "").strip()
        scan_h = int(user_input.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS))

        # One entry per target; unique_id is host:port
        unique = f"{host}:{port}"
        await self.async_set_unique_id(unique)
        self._abort_if_unique_id_configured()

        title = unique
        if sni:
            title = f"{unique} ({sni})"

        return self.async_create_entry(
            title=title,
            data={
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_SNI: sni,
                CONF_SCAN_INTERVAL_HOURS: scan_h,
            },
        )
