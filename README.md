# Öffi Wiener Platz Screensaver

C64-style departure monitor for **Kodi 21** (tested e.g. on LibreELEC 12.2 with Raspberry Pi 4).

The add-on shows live departures at **Wiener Platz (Cologne)** in the look of an old
Commodore terminal: black background, green text, fixed columns, and a header framed
with `*` plus a countdown to the next refresh.

Departure data is fetched from the official JSON endpoint of the VRS departure monitor.

---

## Features

- **Kodi 21 screensaver**  
  Runs as a normal Kodi screensaver (idle / energy saving mode).

- **C64 look & feel**  
  Black background, green “phosphor” text, simple fixed layout.

- **VRS departure data**  
  Uses the JSON API (can be configured in settings dialog):

  `https://www.vrs.de/index.php?eID=tx_vrsinfo_departuremonitor&i=d8f44641a2626fa3ff5a75dd50ca2560`
  create your own source at https://www.vrs.de/fahrplanauskunft/abfahrtsmonitor

  Columns:

  - **LINE** – line number
  - **TYP** – type (U, BUS, etc.)
  - **TIME** – departure time
  - **DELAY** – `!` if delayed
  - **DIRECTION** – direction / destination
  - **STOP** – platform / stop (e.g. “Gleis 2”, “Wiener Platz Bussteig B”)

---

## Requirements

- **Kodi 21 “Omega”**
