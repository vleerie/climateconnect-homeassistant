"""Constants for the ClimateConnect (Itho Daalderop) integration."""
from datetime import timedelta

DOMAIN = "climateconnect"

# How often to poll the boiler's live status/mode. This is separate from
# the login, which only needs to happen once (the session token from
# Azure B2C is valid for about a year).
SCAN_INTERVAL = timedelta(minutes=5)

# Confirmed device mode strings, captured directly from real app traffic.
# "Continuous" ("Continu aan" in the app) takes a temperature; the
# others don't appear to. There may be more modes (e.g. a schedule/
# clock mode) not yet captured -- toggle remaining buttons in the app
# while sniffing to find them, then add here.
MODE_CONTINUOUS = "Continuous"
MODE_SMART_CONTROL = "SmartControl"
MODE_HOLIDAY = "Holiday"
KNOWN_MODES = [MODE_CONTINUOUS, MODE_SMART_CONTROL, MODE_HOLIDAY]
MODES_WITH_TEMPERATURE = {MODE_CONTINUOUS}

DEFAULT_BOOST_TEMPERATURE = 65.0

# Bounds for the target-temperature slider in Home Assistant. These are a
# reasonable guess based on the temperature values captured from real app
# traffic (65.0, 70.0) -- confirm the true min/max by dragging the app's
# "Energieniveau boiler" slider to its extremes while sniffing, then
# adjust these if needed.
MIN_TEMPERATURE = 40.0
MAX_TEMPERATURE = 70.0
