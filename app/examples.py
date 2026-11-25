"""Shared fixtures for the phase 1 API."""

from urllib.parse import urlencode

from . import config, models
from .calendar_links import directions_url

INVITE_URL = f"{config.APP_BASE_URL}/i/demo"
COUPLE = "Priya and Arjun"
LOCATION = "Rose Garden, Amer Road, Jaipur"
CALENDAR_URL = "https://calendar.google.com/calendar/render?" + urlencode({
    "action": "TEMPLATE", "text": f"Sangeet - {COUPLE}",
    "dates": "20261212T180000/20261212T210000", "ctz": "Asia/Kolkata",
    "location": LOCATION, "details": "Added with Card Kholo",
})
FUNCTION = models.Function(
    name="Sangeet", name_original="संगीत", date="2026-12-12", time="18:00",
    venue_name="Rose Garden", venue_address="Amer Road", city="Jaipur",
    gcal_url=CALENDAR_URL,
    maps_url=directions_url(LOCATION),
)
