"""switch platform for ClimateConnect (Itho Daalderop) -- the boost switch."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entries = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ClimateConnectBoostSwitch(item["coordinator"], item["data"]) for item in entries
    )


class ClimateConnectBoostSwitch(CoordinatorEntity, SwitchEntity):
    """The app's "Warm Water Boost" button, as an on/off switch.

    `boostActive` is read back from GetDeviceStatus on every poll, so
    the switch reflects the boiler's real state, not just what we last
    told it to do (e.g. if the boiler auto-clears the boost itself)."""

    _attr_has_entity_name = True
    _attr_name = "Warm water boost"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, data):
        super().__init__(coordinator)
        self._data = data
        self._attr_unique_id = f"{data.serial_number}_boost"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, data.serial_number)})

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get("status", {}).get("boostActive"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_call_with_reauth(
            self._data.client.boost_boiler, self._data.serial_number, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_call_with_reauth(
            self._data.client.boost_boiler, self._data.serial_number, False
        )
        await self.coordinator.async_request_refresh()
