# -*- coding: utf-8 -*-
"""
WIENER PLATZ departure monitor screensaver.
"""

import json
import urllib.request
import urllib.error
import os  # benötigt für Pfadoperationen (QR-Code-Fallback)

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_VERSION = ADDON.getAddonInfo("version")
ADDON_PATH = ADDON.getAddonInfo("path")

# numerische Alignment-Konstante für zentrierten Text (nur X-Richtung)
ALIGN_CENTER_X = 0x00000002


def log(msg, level=xbmc.LOGINFO):
    try:
        xbmc.log(f"[{ADDON_NAME}] {msg}", level)
    except Exception:
        xbmc.log("[screensaver.vrs.wienerplatz] %s" % msg)


def fetch_departures(url):
    """Lädt die Abfahrtsdaten vom VRS-Backend."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"Mozilla/5.0 (Kodi Screensaver {ADDON_VERSION})"
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        data = resp.read().decode(charset, errors="replace")

    payload = json.loads(data)
    updated = payload.get("updated", "")
    events = payload.get("events", [])
    return updated, events


def product_short(product):
    """Produkt zu kompaktem Typ (U, BUS, RB ...) kürzen."""
    if not product:
        return "??"
    p = product.lower()
    if "light" in p:
        return "U"
    if "bus" in p:
        return "BUS"
    if "train" in p or "rail" in p:
        return "RB"
    return product[:3].upper()


def make_header_line(text, width_chars=48):
    """
    Erzeugt eine Zeile der Form:
    ********************
    *   TEXT         *
    ********************
    """
    text = text.strip()
    inner_width = max(0, width_chars - 2)
    if len(text) > inner_width:
        text = text[:inner_width]
    pad_total = inner_width - len(text)
    left_pad = pad_total // 2
    right_pad = pad_total - left_pad
    return "*" + (" " * left_pad) + text + (" " * right_pad) + "*"


class ScreensaverWindow(xbmcgui.Window):
    def __init__(self):
        super().__init__()
        # Header Controls
        self.header_top = None
        self.header_title = None
        self.header_update = None
        self.header_bottom = None
        self.countdown_label = None

        # Tabellen-Controls
        self.col_headers = {}
        self.row_labels = []
        self.max_rows = 10

        # QR-Code Controls
        self.qr_label = None
        self.qr_image = None

        self._build_ui()

    def _build_ui(self):
        # Bildschirmgröße ermitteln
        try:
            width = self.getWidth()
            height = self.getHeight()
            if width <= 0 or height <= 0:
                raise ValueError("invalid size")
        except Exception:
            width, height = 1280, 720

        text_color = "0xFF00FF00"  # C64-Grün
        row_height = 28  # etwas höher für font14

        # Hintergrund
        bg = xbmcgui.ControlImage(0, 0, width, height, "")
        self.addControl(bg)

        # -------------------------
        # Tabellen-Geometrie
        # -------------------------
        gap_x = 10

        col_line_w = 80
        col_typ_w = 80
        col_time_w = 80
        col_delay_w = 90  # breit genug für "DELAY"
        col_dir_w = 340
        col_stop_w = 250

        rel_block_left = 0
        rel_inner_left = rel_block_left

        col_line_x = rel_inner_left
        col_typ_x = col_line_x + col_line_w + gap_x
        col_time_x = col_typ_x + col_typ_w + gap_x
        col_delay_x = col_time_x + col_time_w + gap_x
        col_dir_x = col_delay_x + col_delay_w + gap_x
        col_stop_x = col_dir_x + col_dir_w + gap_x

        content_right = col_stop_x + col_stop_w
        block_width = content_right - rel_block_left

        box_width_px = block_width

        # -------------------------
        # Vertikale Geometrie
        # -------------------------
        rel_y = 0

        rel_header_top_y = rel_y
        rel_header_title_y = rel_header_top_y + row_height
        rel_header_update_y = rel_header_title_y + row_height
        rel_header_bottom_y = rel_header_update_y + row_height
        rel_countdown_y = rel_header_bottom_y + row_height

        rel_table_header_y = rel_countdown_y + row_height
        rel_table_rows_start_y = rel_table_header_y + row_height

        # max_rows so bestimmen, dass alles vertikal passt
        outer_margin_y = 20
        available_height = height - 2 * outer_margin_y
        max_rows = 20
        while max_rows > 1:
            rel_last_row_y = rel_table_rows_start_y + max_rows * row_height
            total_height = rel_last_row_y
            if total_height <= available_height:
                break
            max_rows -= 1
        self.max_rows = max_rows

        rel_last_row_y = rel_table_rows_start_y + self.max_rows * row_height
        total_height = rel_last_row_y

        offset_y = (height - total_height) // 2
        offset_x = (width - block_width) // 2

        def make_label(x, y, w, h, text="", align=0):
            lbl = xbmcgui.ControlLabel(
                int(x + offset_x),
                int(y + offset_y),
                int(w),
                int(h),
                text,
                font="font14",
                textColor=text_color,
                alignment=align,
            )
            self.addControl(lbl)
            return lbl

        # -------------------------
        # Header-Rahmen + Text
        # -------------------------
        header_width_chars = 48
        stars_line = "*" * header_width_chars

        self.header_top = make_label(
            rel_block_left,
            rel_header_top_y,
            box_width_px,
            row_height,
            stars_line,
            align=ALIGN_CENTER_X,
        )
        self.header_title = make_label(
            rel_block_left,
            rel_header_title_y,
            box_width_px,
            row_height,
            make_header_line("WIENER PLATZ DEPARTURES", header_width_chars),
            align=ALIGN_CENTER_X,
        )
        self.header_update = make_label(
            rel_block_left,
            rel_header_update_y,
            box_width_px,
            row_height,
            make_header_line("LAST UPDATE: n/a", header_width_chars),
            align=ALIGN_CENTER_X,
        )
        self.header_bottom = make_label(
            rel_block_left,
            rel_header_bottom_y,
            box_width_px,
            row_height,
            stars_line,
            align=ALIGN_CENTER_X,
        )

        # Countdown-Zeile (zentriert, ohne *)
        self.countdown_label = make_label(
            rel_block_left,
            rel_countdown_y,
            box_width_px,
            row_height,
            "",
            align=ALIGN_CENTER_X,
        )

        # -------------------------
        # Tabellen-Header
        # -------------------------
        self.col_headers["line"] = make_label(
            col_line_x,
            rel_table_header_y,
            col_line_w,
            row_height,
            "LINE",
        )
        self.col_headers["typ"] = make_label(
            col_typ_x,
            rel_table_header_y,
            col_typ_w,
            row_height,
            "TYP",
        )
        self.col_headers["time"] = make_label(
            col_time_x,
            rel_table_header_y,
            col_time_w,
            row_height,
            "TIME",
        )
        # DELAY-Header zentriert
        self.col_headers["delay"] = make_label(
            col_delay_x,
            rel_table_header_y,
            col_delay_w,
            row_height,
            "DELAY",
            align=ALIGN_CENTER_X,
        )
        self.col_headers["dir"] = make_label(
            col_dir_x,
            rel_table_header_y,
            col_dir_w,
            row_height,
            "DIRECTION",
        )
        self.col_headers["stop"] = make_label(
            col_stop_x,
            rel_table_header_y,
            col_stop_w,
            row_height,
            "STOP",
        )

        # -------------------------
        # Datenzeilen
        # -------------------------
        self.row_labels = []
        row_y = rel_table_rows_start_y
        for _ in range(self.max_rows):
            row = {}
            row["line"] = make_label(col_line_x, row_y, col_line_w, row_height, "")
            row["typ"] = make_label(col_typ_x, row_y, col_typ_w, row_height, "")
            row["time"] = make_label(col_time_x, row_y, col_time_w, row_height, "")
            # DELAY-Zellen zentriert, damit '!' mittig steht
            row["delay"] = make_label(
                col_delay_x,
                row_y,
                col_delay_w,
                row_height,
                "",
                align=ALIGN_CENTER_X,
            )
            row["dir"] = make_label(col_dir_x, row_y, col_dir_w, row_height, "")
            row["stop"] = make_label(col_stop_x, row_y, col_stop_w, row_height, "")

            self.row_labels.append(row)
            row_y += row_height

        # -------------------------
        # QR-Code rechts oben
        # -------------------------
        try:
            qr_setting = ADDON.getSetting("qr_image_path") or ""
        except Exception:
            qr_setting = ""

        if qr_setting:
            qr_path = qr_setting
        else:
            # Fallback: mitgeliefertes QR-Bild aus resources
            qr_path = os.path.join(ADDON_PATH, "resources", "wlan_qr.png")
        qr_path = xbmcvfs.translatePath(qr_path)

        qr_size = int(min(width, height) * 0.22)
        qr_margin = 20

        qr_x = width - qr_size - qr_margin
        # oben rechts: etwas unter den oberen Rand, Label direkt darüber
        qr_y = qr_margin + 28  # 28 ~ row_height

        # Label "WLAN ACCESS" oberhalb des QR
        self.qr_label = xbmcgui.ControlLabel(
            int(qr_x),
            int(qr_y - row_height),
            int(qr_size),
            int(row_height),
            "WLAN ACCESS",
            font="font14",
            textColor=text_color,
            alignment=ALIGN_CENTER_X,
        )
        self.addControl(self.qr_label)

        # QR-Bild selbst
        self.qr_image = xbmcgui.ControlImage(
            int(qr_x),
            int(qr_y),
            int(qr_size),
            int(qr_size),
            qr_path,
        )
        self.addControl(self.qr_image)

    # ------------------------------------------------------------------
    # API für Hauptloop
    # ------------------------------------------------------------------
    def set_update_text(self, updated):
        header_width_chars = 48
        if updated:
            text = f"LAST UPDATE: {updated}"
        else:
            text = "LAST UPDATE: n/a"
        line = make_header_line(text, header_width_chars)
        self.header_update.setLabel(line)

    def set_countdown(self, seconds_remaining):
        text = f"-- next refresh in {seconds_remaining:2d} s --"
        self.countdown_label.setLabel(text)

    def set_data(self, events):
        rows_to_show = min(self.max_rows, len(events))

        for idx in range(self.max_rows):
            row = self.row_labels[idx]
            if idx < rows_to_show:
                ev = events[idx]
                stop = (ev.get("stopPoint") or {}).get("name", "") or ""
                dep = ev.get("departure") or {}
                line = ev.get("line") or {}

                line_no = str(line.get("number", ""))
                prod = product_short(line.get("product"))
                est = dep.get("estimate") or dep.get("timetable") or "--:--"
                delayed = dep.get("delayed")
                delay_flag = "!" if delayed else ""

                direction = line.get("direction", "") or ""

                if len(direction) > 32:
                    direction = direction[:31] + "…"
                if len(stop) > 24:
                    stop = stop[:23] + "…"

                row["line"].setLabel(line_no)
                row["typ"].setLabel(prod)
                row["time"].setLabel(est)
                row["delay"].setLabel(delay_flag)
                row["dir"].setLabel(direction)
                row["stop"].setLabel(stop)
            else:
                row["line"].setLabel("")
                row["typ"].setLabel("")
                row["time"].setLabel("")
                row["delay"].setLabel("")
                row["dir"].setLabel("")
                row["stop"].setLabel("")

            # leichte Verzögerung für Top-Down-Update
            xbmc.sleep(40)

    def onAction(self, action):
        # Beliebige Taste beendet den Screensaver
        self.close()

    def onClick(self, controlId):
        self.close()


def run():
    monitor = xbmc.Monitor()

    url = (
        ADDON.getSetting("url")
        or "https://www.vrs.de/index.php?eID=tx_vrsinfo_departuremonitor&i=d8f44641a2626fa3ff5a75dd50ca2560"
    )
    try:
        interval = int(ADDON.getSetting("refresh_interval") or "30")
    except ValueError:
        interval = 30

    log(f"Starting screensaver {ADDON_VERSION}, url={url}, interval={interval}s")

    win = ScreensaverWindow()
    win.show()

    try:
        while not monitor.abortRequested():
            updated = ""
            events = []
            try:
                updated, events = fetch_departures(url)
                log(f"Fetched departures, {len(events)} events.")
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                log(f"Network error: {e}", xbmc.LOGWARNING)
            except Exception as e:
                log(f"Unexpected error while fetching: {e}", xbmc.LOGERROR)

            # Header + Tabelle aktualisieren
            win.set_update_text(updated)
            win.set_data(events)

            # Countdown
            remaining = interval
            while remaining > 0 and not monitor.abortRequested():
                win.set_countdown(remaining)
                if monitor.waitForAbort(1):
                    break
                remaining -= 1

            if monitor.abortRequested():
                break
    finally:
        log("Stopping screensaver.")
        try:
            win.close()
        except Exception:
            pass


# unguarded Aufruf, damit Kodi den Screensaver sicher startet
run()
