"""
Unofficial ClimateConnect (Itho Daalderop) API client.

Reverse-engineered from the official Android app's own network traffic,
for personal use controlling your own boiler/device. All requests here
are synchronous (plain `requests`) -- Home Assistant callers must run
them via `hass.async_add_executor_job(...)`, never on the event loop
directly.
"""

import base64
import json
import re
from urllib.parse import urlparse, parse_qs

import requests

BASE_URL = "https://itho-tussenlaag.bettywebblocks.com"
DEVICE_API_URL = "https://wifi-api.id-c.net"
CALLBACK_URL = "https://services.climateforlife.nl/sso/callback"
TENANT = "climateforlifeportal.onmicrosoft.com"
POLICY = "B2C_1_SignUpandSignIn"
B2C_HOST = "climateforlifeportal.b2clogin.com"
# Identifies the ClimateConnect Android app itself to the backend
# (same value for every user, not tied to your personal account).
APPLICATION_ID = "2da3d256-ca0a-4041-84ba-93856efceef9"

COMMON_HEADERS = {
    "user-agent": "okhttp/5.3.2",
    "accept-encoding": "gzip",
}


class ClimateConnectAuthError(Exception):
    """Raised when login fails (bad credentials, or the flow's HTML/JS
    structure has changed upstream and our scraping no longer matches)."""


def _decode_jwt_payload(token: str) -> dict:
    """Decode a JWT's payload without verifying the signature -- fine
    here since we trust our own freshly-completed login."""
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # restore stripped padding
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def login(email: str, password: str) -> dict:
    """Runs the full Azure B2C OAuth flow and returns session info:
    {state, application_id, user, expires_at, refresh_token, raw_token}."""
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)

    try:
        # 1. Ask the Itho backend for the B2C authorize URL to use.
        r = session.get(
            f"{BASE_URL}/sso/initiate",
            params={"redirect": "climateconnect://login", "application_id": APPLICATION_ID},
            timeout=30,
        )
        r.raise_for_status()
        sso_url = r.json()["sso"]

        # 2. Load the B2C login page to scrape the CSRF token + transId.
        r = session.get(sso_url, timeout=30)
        r.raise_for_status()
        html = r.text
        csrf = re.search(r'"csrf":"([^"]+)"', html).group(1)
        trans_id = re.search(r'"transId":"([^"]+)"', html).group(1)

        # 3. Submit the actual credentials.
        self_asserted_url = f"https://{B2C_HOST}/{TENANT}/{POLICY}/SelfAsserted"
        r = session.post(
            self_asserted_url,
            params={"tx": trans_id, "p": POLICY},
            headers={
                "X-CSRF-TOKEN": csrf,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
            data={
                "request_type": "RESPONSE",
                "logonIdentifier": email,
                "password": password,
            },
            timeout=30,
        )
        r.raise_for_status()
        if r.json().get("status") != "200":
            raise ClimateConnectAuthError(f"Login rejected by server: {r.text}")

        # 4. Confirm sign-in; get back an auto-submitting form with code+state.
        confirm_url = f"https://{B2C_HOST}/{TENANT}/{POLICY}/api/CombinedSigninAndSignup/confirmed"
        r = session.get(
            confirm_url, params={"csrf_token": csrf, "tx": trans_id, "p": POLICY}, timeout=30
        )
        r.raise_for_status()
        state_val = re.search(r"name='state' id='state' value='([^']+)'", r.text).group(1)
        code_val = re.search(r"name='code' id='code' value='([^']+)'", r.text).group(1)

        # 5. Submit code+state to Itho's callback; get a 302 with our JWT.
        r = session.post(
            CALLBACK_URL,
            data={"state": state_val, "code": code_val},
            allow_redirects=False,
            timeout=30,
        )
        location = r.headers.get("Location", "")
        if "token=" not in location:
            raise ClimateConnectAuthError(f"No token in callback redirect: {location}")
        token = parse_qs(urlparse(location).query)["token"][0]
    except ClimateConnectAuthError:
        raise
    except (requests.RequestException, KeyError, AttributeError, ValueError) as err:
        raise ClimateConnectAuthError(f"Login flow failed: {err}") from err

    payload = _decode_jwt_payload(token)
    session_info = payload["session"]
    return {
        "state": session_info["state"],
        "application_id": session_info["application_id"],
        "user": payload.get("user", {}),
        "expires_at": session_info.get("expires_at"),
        "refresh_token": session_info.get("refresh_token"),
        "raw_token": token,
    }


class ClimateConnectClient:
    """Wraps both known backends:
    - itho-tussenlaag.bettywebblocks.com (device list, profile)
      auth: `state` + `application-id` headers
    - wifi-api.id-c.net (device mode, boost, status)
      auth: `Authorization: Bearer <raw JWT>`
    """

    def __init__(self, state: str, application_id: str, raw_token: str):
        self.session = requests.Session()
        self.session.headers.update(
            {**COMMON_HEADERS, "state": state, "application-id": application_id}
        )
        self.device_session = requests.Session()
        self.device_session.headers.update(
            {**COMMON_HEADERS, "Authorization": f"Bearer {raw_token}"}
        )

    # --- itho-tussenlaag.bettywebblocks.com ---

    def update_credentials(self, state: str, application_id: str, raw_token: str) -> None:
        """Swap in fresh credentials after a re-login, without needing
        callers to replace their reference to this client object."""
        self.session.headers.update({"state": state, "application-id": application_id})
        self.device_session.headers.update({"Authorization": f"Bearer {raw_token}"})

    def get_devices(self) -> dict:
        r = self.session.get(f"{BASE_URL}/api/consumer-app/device", timeout=30)
        r.raise_for_status()
        return r.json()

    # --- wifi-api.id-c.net ---

    def get_device_mode(self, serial_number: str) -> dict:
        r = self.device_session.get(
            f"{DEVICE_API_URL}/api/GetDeviceMode",
            params={"serialNumber": serial_number},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def get_device_status(self, serial_number: str) -> dict:
        r = self.device_session.get(
            f"{DEVICE_API_URL}/api/GetDeviceStatus",
            params={"serialNumber": serial_number},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def set_device_mode(
        self, serial_number: str, device_mode: str, temperature: float | None = None
    ) -> None:
        body = {"deviceMode": device_mode, "serialNumber": serial_number}
        if temperature is not None:
            body["temperature"] = temperature
        r = self.device_session.post(
            f"{DEVICE_API_URL}/api/UpdateDeviceMode",
            json=body,
            timeout=30,
        )
        r.raise_for_status()

    def boost_boiler(self, serial_number: str, activate: bool = True) -> None:
        r = self.device_session.post(
            f"{DEVICE_API_URL}/api/BoostBoiler",
            json={"activateBoost": activate, "serialNumber": serial_number},
            timeout=30,
        )
        r.raise_for_status()
