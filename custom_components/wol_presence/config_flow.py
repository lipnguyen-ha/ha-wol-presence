"""Config and options flow for WOL + Presence."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import format_mac

from .const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_METHOD,
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    METHOD_PING,
    METHOD_TCP,
)
from .wol import build_magic_packet


def _schema(current: dict[str, Any], with_name: bool) -> vol.Schema:
    """Build the form, pre-filled with the values shown to the user."""
    fields: dict[Any, Any] = {}

    if with_name:
        fields[vol.Required(CONF_NAME, default=current.get(CONF_NAME, ""))] = (
            selector.TextSelector()
        )

    fields[vol.Required(CONF_MAC, default=current.get(CONF_MAC, ""))] = (
        selector.TextSelector()
    )
    fields[vol.Required(CONF_HOST, default=current.get(CONF_HOST, ""))] = (
        selector.TextSelector()
    )
    fields[vol.Required(CONF_METHOD, default=current.get(CONF_METHOD, METHOD_PING))] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[METHOD_PING, METHOD_TCP],
                translation_key="method",
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    )
    fields[vol.Optional(CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT))] = (
        selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=65535, step=1, mode=selector.NumberSelectorMode.BOX
            )
        )
    )
    fields[
        vol.Optional(
            CONF_BROADCAST_ADDRESS,
            default=current.get(CONF_BROADCAST_ADDRESS, DEFAULT_BROADCAST_ADDRESS),
        )
    ] = selector.TextSelector()
    fields[
        vol.Optional(
            CONF_BROADCAST_PORT,
            default=current.get(CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT),
        )
    ] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=65535, step=1, mode=selector.NumberSelectorMode.BOX
        )
    )
    fields[
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    ] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=5,
            max=3600,
            step=1,
            unit_of_measurement="s",
            mode=selector.NumberSelectorMode.BOX,
        )
    )

    return vol.Schema(fields)


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    """Return per-field errors, empty when the input is usable."""
    errors: dict[str, str] = {}

    try:
        build_magic_packet(user_input[CONF_MAC])
    except ValueError:
        errors[CONF_MAC] = "invalid_mac"

    if user_input[CONF_METHOD] == METHOD_TCP and not int(
        user_input.get(CONF_PORT) or 0
    ):
        errors[CONF_PORT] = "port_required"

    return errors


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """Numbers arrive from the UI as floats; store them as ints."""
    data = dict(user_input)
    data[CONF_MAC] = format_mac(data[CONF_MAC]).upper()
    for key, default in (
        (CONF_PORT, DEFAULT_PORT),
        (CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT),
        (CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    ):
        data[key] = int(data.get(key) or default)
    data[CONF_BROADCAST_ADDRESS] = (data.get(CONF_BROADCAST_ADDRESS) or "").strip()
    return data


class WolPresenceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle adding a device from the UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The form shown by Add Integration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                data = _normalize(user_input)
                await self.async_set_unique_id(format_mac(data[CONF_MAC]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}, with_name=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return WolPresenceOptionsFlow()


class WolPresenceOptionsFlow(OptionsFlow):
    """Edit an existing device via Configure."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=_normalize(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or current, with_name=False),
            errors=errors,
        )
