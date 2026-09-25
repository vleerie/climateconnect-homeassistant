# ClimateConnect (Itho Daalderop) for Home Assistant

Unofficial Home Assistant integration for Itho Daalderop boilers that use
the ClimateConnect app (e.g. the Smartboiler). Built by reverse-engineering
the official Android app's own network traffic.

## ⚠️ Disclaimer

- This is **not** made, endorsed, or supported by Itho Daalderop.
- It relies on undocumented, reverse-engineered API endpoints that Itho
  Daalderop could change or block at any time, breaking this integration
  without warning.
- Use at your own risk. The authors take no responsibility for anything
  this integration does or fails to do to your device.
- You need your own valid ClimateConnect account and credentials -- this
  integration does not create or share accounts.

## Features

- **Water heater entity**: view and set the boiler's operating mode
  (`Continuous`, `SmartControl`, `Holiday`) and target temperature
- **Boost switch**: turn the "Warm Water Boost" function on/off, with
  live status
- **Diagnostic sensors**: legionella-prevention timer, energy
  consumption, device online/offline state
- **Automatic re-login**: if the session token is ever rejected, the
  integration logs back in automatically using your stored credentials

## Known limitations

- Only supports the **first device** on your account. If you have
  multiple boilers, only one will show up (contributions to add
  multi-device support are welcome).
- The confirmed operating modes are `Continuous`, `SmartControl`, and
  `Holiday`. There may be others (e.g. a schedule/clock mode) not yet
  captured.
- The temperature range (40-70°C) is an estimate based on values seen
  in real traffic, not a confirmed hardware limit.
- There is **no way to manually trigger the anti-legionella cycle** --
  the official app doesn't offer this either, and no such API endpoint
  has been confirmed to exist.

## Installation (via HACS)

1. In Home Assistant, go to **HACS** → the three-dot menu (top right) →
   **Custom repositories**
2. Add this repository's URL, category **Integration**
3. Find "ClimateConnect (Itho Daalderop)" in HACS and install it
4. Restart Home Assistant
5. **Settings → Devices & services → Add integration** → search for
   "ClimateConnect"
6. Enter your ClimateConnect email and password

## Manual installation

Copy the `custom_components/climateconnect` folder into your Home
Assistant `config/custom_components/` directory, then restart Home
Assistant and follow steps 5-6 above.

## Contributing

Found another device mode, the real temperature range, or the
legionella-cycle endpoint by sniffing your own app traffic? Pull
requests welcome -- see `const.py` for where the known values live.

## License

MIT -- see LICENSE.
