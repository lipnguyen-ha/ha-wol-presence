"""Constants for the WOL + Presence integration."""

DOMAIN = "wol_presence"

CONF_METHOD = "method"
CONF_BROADCAST_ADDRESS = "broadcast_address"
CONF_BROADCAST_PORT = "broadcast_port"

METHOD_PING = "ping"
METHOD_TCP = "tcp"

GLOBAL_BROADCAST = "255.255.255.255"
# Empty means "derive from the device IP" - see wol.derive_broadcast().
DEFAULT_BROADCAST_ADDRESS = ""
DEFAULT_BROADCAST_PORT = 9
DEFAULT_SCAN_INTERVAL = 30
# Any closed port proves the host is awake (it answers with RST), so a high
# unused port is the safest default for the TCP probe.
DEFAULT_PORT = 54321

# Mirrors the ESP8266 firmware this replaces: probe twice before declaring a
# device offline, and poll fast for a while right after a magic packet.
PROBE_TIMEOUT = 2
PROBE_RETRIES = 2
BOOST_INTERVAL = 5
BOOST_DURATION = 120
WOL_REPEATS = 3
