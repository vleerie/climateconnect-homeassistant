"""The ClimateConnect (Itho Daalderop) integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ClimateConnectAuthError, ClimateConnectClient, login
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.WATER_HEATER, Platform.SWITCH, Platform.SENSOR]


@dataclass
class ClimateConnectData:
    """Runtime data made available to every entity via its coordinator."""

    client: ClimateConnectClient
    serial_number: str
    device_info: dict


class ClimateConnectCoordinator(DataUpdateCoordinator[dict]):
    """Polls GetDeviceMode + GetDeviceStatus for one device on a fixed
    interval, and transparently re-logs-in and retries once if the
    token is rejected (e.g. after the ~1 year validity expires)."""

    def __init__(
        self, hass: HomeAssistant, client: ClimateConnectClient, serial_number: str,
        email: str, password: str,
    ):
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_{serial_number}", update_interval=SCAN_INTERVAL)
        self.client = client
        self.serial_number = serial_number
        self._email = email
        self._password = password

    async def _relogin(self) -> None:
        """Runs a fresh login and swaps the new credentials into the
        existing client object in place."""
        _LOGGER.info("ClimateConnect token rejected; logging in again")
        creds = await self.hass.async_add_executor_job(login, self._email, self._password)
        self.client.update_credentials(creds["state"], creds["application_id"], creds["raw_token"])

    async def async_call_with_reauth(self, func: Callable, *args: Any) -> Any:
        """Runs a synchronous client method in the executor; on a 401/403
        it re-logs-in once and retries the same call before giving up."""
        try:
            return await self.hass.async_add_executor_job(func, *args)
        except requests.HTTPError as err:
            status = err.response.status_code if err.response is not None else None
            if status not in (401, 403):
                raise
            try:
                await self._relogin()
            except ClimateConnectAuthError as auth_err:
                raise ConfigEntryAuthFailed(
                    f"Re-login failed after token was rejected: {auth_err}"
                ) from auth_err
            return await self.hass.async_add_executor_job(func, *args)

    async def _async_update_data(self) -> dict:
        try:
            mode = await self.async_call_with_reauth(self.client.get_device_mode, self.serial_number)
            status = await self.async_call_with_reauth(self.client.get_device_status, self.serial_number)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Error talking to ClimateConnect: {err}") from err

        return {"mode": mode.get("result", {}), "status": status.get("result", {})}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Log in once, then set up one coordinator + entity set per device
    found on the account (most accounts have one boiler, but this
    supports accounts with several)."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    try:
        creds = await hass.async_add_executor_job(login, email, password)
    except ClimateConnectAuthError as err:
        raise ConfigEntryAuthFailed(f"ClimateConnect login failed: {err}") from err

    client = ClimateConnectClient(creds["state"], creds["application_id"], creds["raw_token"])

    try:
        devices = await hass.async_add_executor_job(client.get_devices)
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(f"Could not fetch ClimateConnect devices: {err}") from err

    device_list = devices.get("devices", [])
    if not device_list:
        raise ConfigEntryNotReady("ClimateConnect returned no devices for this account")

    entries: list[dict] = []
    for device_info in device_list:
        serial_number = device_info["serial_number"].lstrip("#")
        # Every device shares the same login session/client; only the
        # serial number (and therefore the coordinator) differs.
        coordinator = ClimateConnectCoordinator(hass, client, serial_number, email, password)
        await coordinator.async_config_entry_first_refresh()
        entries.append(
            {
                "coordinator": coordinator,
                "data": ClimateConnectData(
                    client=client, serial_number=serial_number, device_info=device_info
                ),
            }
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entries

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
