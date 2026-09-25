"""water_heater platform for ClimateConnect (Itho Daalderop)."""
from __future__ import annotations

import logging

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KNOWN_MODES, MIN_TEMPERATURE, MAX_TEMPERATURE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entries = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ClimateConnectWaterHeater(item["coordinator"], item["data"], entry) for item in entries
    )


class ClimateConnectWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Represents the boiler's mode + temperature (the app's "Modus" and
    "Energieniveau boiler" controls)."""

    _attr_has_entity_name = True
    _attr_name = None  # use the device name as the entity name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE
    )
    # Only "Continuous" is confirmed from captured traffic so far. The
    # app has other mode buttons (off, eco, schedule) whose exact API
    # string values aren't captured yet -- add them here once known.
    _attr_operation_list = KNOWN_MODES
    _attr_min_temp = MIN_TEMPERATURE
    _attr_max_temp = MAX_TEMPERATURE

    def __init__(self, coordinator, data, entry: ConfigEntry):
        super().__init__(coordinator)
        self._data = data
        self._attr_unique_id = f"{data.serial_number}_water_heater"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.serial_number)},
            name=data.device_info.get("product_registration", {}).get(
                "item_name", "ClimateConnect boiler"
            ),
            manufacturer="Itho Daalderop",
            model=data.device_info.get("product_registration", {}).get("item_code"),
            sw_version=(coordinator.data or {}).get("status", {}).get("deviceSoftwareVersion"),
        )

    @property
    def current_temperature(self) -> float | None:
        return (self.coordinator.data or {}).get("mode", {}).get("temperature")

    @property
    def target_temperature(self) -> float | None:
        return (self.coordinator.data or {}).get("mode", {}).get("temperature")

    @property
    def current_operation(self) -> str | None:
        return (self.coordinator.data or {}).get("mode", {}).get("deviceMode")

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        current_mode = self.current_operation or KNOWN_MODES[0]
        await self.coordinator.async_call_with_reauth(
            self._data.client.set_device_mode,
            self._data.serial_number,
            current_mode,
            float(temperature),
        )
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        from .const import MODES_WITH_TEMPERATURE

        temp = None
        if operation_mode in MODES_WITH_TEMPERATURE:
            temp = self.target_temperature or 65.0
        await self.coordinator.async_call_with_reauth(
            self._data.client.set_device_mode,
            self._data.serial_number,
            operation_mode,
            temp,
        )
        await self.coordinator.async_request_refresh()
