"""Presence polling for WOL + Presence."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    BOOST_DURATION,
    BOOST_INTERVAL,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_METHOD,
    DEFAULT_BROADCAST_PORT,
    DEFAULT_SCAN_INTERVAL,
    METHOD_TCP,
    PROBE_RETRIES,
    PROBE_TIMEOUT,
)
from .wol import derive_broadcast, send_magic_packet

_LOGGER = logging.getLogger(__name__)


async def async_ping_alive(host: str) -> bool:
    """ICMP probe via the ping binary shipped with the HA container."""
    cmd = ("ping", "-c", "1", "-W", str(PROBE_TIMEOUT), host)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except OSError as err:
        _LOGGER.error("Cannot run ping %s: %s", " ".join(cmd), err)
        return False
    except Exception:  # noqa: BLE001
        # HA's event-loop protection raises RuntimeError for blocking calls;
        # without this branch the failure is invisible in the log.
        _LOGGER.exception("ping %s could not be started", host)
        return False

    try:
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), PROBE_TIMEOUT + 2
        )
    except (TimeoutError, asyncio.TimeoutError):
        proc.kill()
        await proc.wait()
        _LOGGER.debug("ping %s: killed after %ss", host, PROBE_TIMEOUT + 2)
        return False

    alive = proc.returncode == 0
    _LOGGER.debug(
        "ping %s: rc=%s alive=%s output=%r",
        host,
        proc.returncode,
        alive,
        stdout.decode(errors="replace").strip(),
    )
    return alive


async def async_tcp_alive(host: str, port: int) -> bool:
    """TCP probe.

    A SYN-ACK (port open) and an RST (port closed) both prove the host is
    awake; only silence means it is asleep or gone. This is what makes the
    probe usable on Macs, whose NIC answers ICMP while the machine sleeps.
    """
    writer = None
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), PROBE_TIMEOUT
        )
    except ConnectionRefusedError:
        _LOGGER.debug("tcp %s:%s: refused (RST) -> awake", host, port)
        return True  # RST - host is awake, port simply closed
    except (TimeoutError, asyncio.TimeoutError):
        _LOGGER.debug("tcp %s:%s: timeout -> asleep or filtered", host, port)
        return False
    except OSError as err:
        _LOGGER.debug("tcp %s:%s: %s -> asleep", host, port, err)
        return False
    finally:
        if writer is not None:
            writer.close()
    _LOGGER.debug("tcp %s:%s: connected -> awake", host, port)
    return True


class WolPresenceCoordinator(DataUpdateCoordinator[bool]):
    """Polls one device and sends its magic packets."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._cancel_boost: CALLBACK_TYPE | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=self._scan_interval(entry)),
        )

    @staticmethod
    def _scan_interval(entry: ConfigEntry) -> int:
        cfg = {**entry.data, **entry.options}
        return int(cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    @property
    def cfg(self) -> dict:
        """Options override data, so edits from the UI take effect."""
        return {**self.entry.data, **self.entry.options}

    async def _async_update_data(self) -> bool:
        cfg = self.cfg
        host = cfg[CONF_HOST]
        use_tcp = cfg.get(CONF_METHOD) == METHOD_TCP
        port = int(cfg.get(CONF_PORT) or 0)

        # A single silent probe is not enough - retry before calling it offline.
        for attempt in range(1, PROBE_RETRIES + 1):
            if use_tcp:
                alive = await async_tcp_alive(host, port)
            else:
                alive = await async_ping_alive(host)
            if alive:
                _LOGGER.debug(
                    "%s: online (%s probe, attempt %s)",
                    host,
                    "tcp" if use_tcp else "ping",
                    attempt,
                )
                return True
        _LOGGER.debug(
            "%s: offline after %s %s probes",
            host,
            PROBE_RETRIES,
            "tcp" if use_tcp else "ping",
        )
        return False

    async def async_wake(self) -> None:
        """Send the magic packet, then poll fast until the device shows up."""
        cfg = self.cfg
        broadcast = cfg.get(CONF_BROADCAST_ADDRESS) or derive_broadcast(cfg[CONF_HOST])
        await self.hass.async_add_executor_job(
            send_magic_packet,
            cfg[CONF_MAC],
            broadcast,
            int(cfg.get(CONF_BROADCAST_PORT) or DEFAULT_BROADCAST_PORT),
        )
        self._start_boost()
        await self.async_request_refresh()

    def _start_boost(self) -> None:
        if self._cancel_boost is not None:
            self._cancel_boost()
        self.update_interval = timedelta(seconds=BOOST_INTERVAL)
        self._cancel_boost = async_call_later(
            self.hass, BOOST_DURATION, self._end_boost
        )

    @callback
    def _end_boost(self, _now) -> None:
        self._cancel_boost = None
        self.update_interval = timedelta(seconds=self._scan_interval(self.entry))

    @callback
    def async_shutdown_boost(self) -> None:
        if self._cancel_boost is not None:
            self._cancel_boost()
            self._cancel_boost = None
