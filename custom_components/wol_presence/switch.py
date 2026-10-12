"""Switch that wakes a device and reports whether it is awake."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_METHOD, DOMAIN, METHOD_TCP
from .coordinator import WolPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch for this device."""
    async_add_entities([WolPresenceSwitch(entry.runtime_data, entry)])


class WolPresenceSwitch(CoordinatorEntity[WolPresenceCoordinator], SwitchEntity):
    """Turn on sends a magic packet; the state comes from the presence probe."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_assumed_state = False

    def __init__(
        self, coordinator: WolPresenceCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            connections={
                (CONNECTION_NETWORK_MAC, format_mac(coordinator.cfg[CONF_MAC]))
            },
            name=entry.title,
            manufacturer="Wake on LAN",
        )

    @property
    def is_on(self) -> bool:
        """True when the last probe found the device awake."""
        return bool(self.coordinator.data)

    @property
    def icon(self) -> str:
        """Both names must exist in MDI - an unknown name renders as blank."""
        return "mdi:monitor" if self.is_on else "mdi:monitor-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cfg = self.coordinator.cfg
        attrs = {
            "mac": cfg[CONF_MAC],
            "host": cfg[CONF_HOST],
            "probe": cfg.get(CONF_METHOD),
        }
        if cfg.get(CONF_METHOD) == METHOD_TCP:
            attrs["probe_port"] = int(cfg.get(CONF_PORT) or 0)
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Send the magic packet."""
        await self.coordinator.async_wake()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Wake on LAN cannot power a device down - just re-check its state."""
        await self.coordinator.async_request_refresh()
