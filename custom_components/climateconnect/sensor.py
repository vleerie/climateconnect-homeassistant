"""sensor platform for ClimateConnect (Itho Daalderop) -- diagnostic values."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entries = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for item in entries:
        coordinator, data = item["coordinator"], item["data"]
        entities += [
            LegionellaTimerSensor(coordinator, data),
            EnergyConsumptionSensor(coordinator, data),
            DeviceStateSensor(coordinator, data),
        ]
    async_add_entities(entities)


class _BaseClimateConnectSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, data):
        super().__init__(coordinator)
        self._data = data
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, data.serial_number)})


class LegionellaTimerSensor(_BaseClimateConnectSensor):
    """Hours remaining until the boiler's automatic anti-legionella cycle.

    This is read-only -- the app has no button to trigger the cycle
    manually, and no such endpoint has been confirmed in captured
    traffic (see the legionella_probe.py script for testing candidates)."""

    _attr_name = "Legionella preventie timer"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_icon = "mdi:water-thermometer"

    def __init__(self, coordinator, data):
        super().__init__(coordinator, data)
        self._attr_unique_id = f"{data.serial_number}_legionella_timer"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("status", {}).get("legionellaPreventionTimer")


class EnergyConsumptionSensor(_BaseClimateConnectSensor):
    """Energy consumption as reported by GetDeviceStatus. The exact
    measurement period (today, current cycle, etc.) isn't confirmed from
    captured traffic, so this is exposed as a plain measurement rather
    than a total/statistics-tracked energy sensor."""

    _attr_name = "Energieverbruik"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator, data):
        super().__init__(coordinator, data)
        self._attr_unique_id = f"{data.serial_number}_energy_consumption"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("status", {}).get("energyConsumption")


class DeviceStateSensor(_BaseClimateConnectSensor):
    """Online/offline connectivity state of the boiler."""

    _attr_name = "Apparaatstatus"
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, data):
        super().__init__(coordinator, data)
        self._attr_unique_id = f"{data.serial_number}_device_state"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("status", {}).get("deviceState")
