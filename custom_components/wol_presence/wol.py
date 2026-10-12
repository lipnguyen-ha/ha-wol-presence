"""Magic packet construction and sending."""

from __future__ import annotations

import ipaddress
import logging
import socket

from .const import GLOBAL_BROADCAST, WOL_REPEATS

_LOGGER = logging.getLogger(__name__)

_HEX = "0123456789abcdefABCDEF"


def build_magic_packet(mac: str) -> bytes:
    """Return the 102 byte magic packet for a MAC address."""
    hexstr = "".join(c for c in mac if c in _HEX)
    if len(hexstr) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    return b"\xff" * 6 + bytes.fromhex(hexstr) * 16


def derive_broadcast(host: str) -> str:
    """Subnet broadcast for a host address, assuming a /24 home LAN.

    192.168.0.105 -> 192.168.0.255. Falls back to the global broadcast for
    anything that is not a plain IPv4 address.
    """
    try:
        network = ipaddress.ip_network(f"{host}/24", strict=False)
    except ValueError:
        return GLOBAL_BROADCAST
    return str(network.broadcast_address)


def send_magic_packet(mac: str, address: str, port: int) -> bool:
    """Send the magic packet. Blocking - call from an executor."""
    packet = build_magic_packet(mac)

    # Send to the configured broadcast address and, if it differs, to the
    # global broadcast as well. Some routers forward only one of the two.
    targets = [address]
    if address != GLOBAL_BROADCAST:
        targets.append(GLOBAL_BROADCAST)

    sent = False
    for _ in range(WOL_REPEATS):
        for target in targets:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.sendto(packet, (target, port))
                sent = True
            except OSError as err:
                _LOGGER.debug("Magic packet to %s:%s failed: %s", target, port, err)
    return sent
