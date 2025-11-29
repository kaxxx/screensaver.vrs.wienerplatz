# -*- coding: utf-8 -*-
"""
WIENER PLATZ departure monitor screensaver.
"""

import json
import urllib.request
import urllib.error

import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
ADDON_VERSION = ADDON.getAddonInfo("version")

# numerische Alignment-Konstante für zentrierten Text (nur X-Richtung)
ALIGN_CENTER_X = 0x00000002


def log(msg, level=xbmc.LOGINFO):
    try:
        xbmc.log(f"[{ADDON_NAME}] {msg}", level)
    except Exception:
        xbmc.log("[screensaver.vrs.wienerplatz] %s" % msg)


def fetch_departures(url):
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


class ScreensaverWindow(xbmcgui.Window):
    def __init__(self):
        super().__init__()
        # Header Controls
        self.header_top = None
        self.header_bottom = None
        self.header_title_center = None
        self.header_update_center = None
        self.countdown_label = None

        # Sternchen für das Blinken
        self.star_top_left = None
        self.star_top_right = None
        self.star_bottom_left = None
        self.star_bottom_right = None

        # Tabellen-Controls
        self.col_headers = {}
        self.row_labels = []
        self.max_rows = 10

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
        row_height = 24

        # Hintergrund
        bg = xbmcgui.ControlImage(0, 0, width, height, "")
        self.addControl(bg)

        # -------------------------
        # Horizontale Geometrie
        # -------------------------
        gap_x = 10

        col_line_w = 80
        col_typ_w = 80
        col_time_w = 80
        col_del_w = 60
        col_dir_w = 360
        col_stop_w = 260

        rel_block_left = 0
        rel_inner_left = rel_block_left

        col_line_x = rel_inner_left
        col_typ_x = col_line_x + col_line_w + gap_x
        col_time_x = col_typ_x + col_typ_w + gap_x
        col_del_x = col_time_x + col_time_w + gap_x
        col_dir_x = col_del_x + col_del_w + gap_x
        col_stop_x = col_dir_x + col_dir_w + gap_x

        content_right = col_stop_x + col_stop_w
        block_width = content_right - rel_block_left

        box_width_px = block_width
        star_col_width = 20  # Breite der linken/rechten Stern-Spalte in Pixeln

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
                font="font13",
                textColor=text_color,
                alignment=align,
            )
            self.addControl(lbl)
            return lbl

        # -------------------------
        # Header-Rahmen + Text
        # -------------------------
        stars_line = "*" * 64  # dekorative obere/untere Linie

        # Obere Sternlinie (komplett über der Breite)
        self.header_top = make_label(
            rel_block_left,
            rel_header_top_y,
            box_width_px,
            row_height,
            stars_line,
            align=ALIGN_CENTER_X,
        )

        # Titelzeile: *  [zentrierter Text]  *
        title_inner_width = box_width_px - 2 * star_col_width
        # linker Stern (oben)
        self.star_top_left = make_label(
            rel_block_left,
            rel_header_title_y,
            star_col_width,
            row_height,
            "*",
            align=ALIGN_CENTER_X,
        )
        # zentrierter Titeltext
        self.header_title_center = make_label(
            rel_block_left + star_col_width,
            rel_header_title_y,
            title_inner_width,
            row_height,
            "WIENER PLATZ DEPARTURES",
            align=ALIGN_CENTER_X,
        )
        # rechter Stern (oben)
        self.star_top_right = make_label(
            rel_block_left + box_width_px - star_col_width,
            rel_header_title_y,
            star_col_width,
            row_height,
            "*",
            align=ALIGN_CENTER_X,
        )

        # Update-Zeile: *  [zentrierter Text]  *
        self.star_bottom_left = make_label(
            rel_block_left,
            rel_header_update_y,
            star_col_width,
            row_height,
            "*",
            align=ALIGN_CENTER_X,
        )
        self.header_update_center = make_label(
            rel_block_left + star_col_width,
            rel_header_update_y,
            title_inner_width,
            row_height,
            "LAST UPDATE: n/a",
            align=ALIGN_CENTER_X,
        )
        self.star_bottom_right = make_label(
            rel_block_left + box_width_px - star_col_width,
            rel_header_update_y,
            star_col_width,
            row_height,
            "*",
            align=ALIGN_CENTER_X,
        )

        # Untere Sternlinie
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
        # DEL-Header jetzt zentriert, damit er optisch mit dem '!' in den Datenzeilen fluchtet
        self.col_headers["del"] = make_label(
            col_del_x,
            rel_table_header_y,
            col_del_w,
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
        row_y = rel_table_rows_start_y
        for _ in range(self.max_rows):
            row = {}
            row["line"] = make_label(col_line_x, row_y, col_line_w, row_height, "")
            row["typ"] = make_label(col_typ_x, row_y, col_typ_w, row_height, "")
            row["time"] = make_label(col_time_x, row_y, col_time_w, row_height, "")
            # DEL-Zellen zentriert, damit '!' mittig steht
            row["del"] = make_label(
                col_del_x, row_y, col_del_w, row_height, "", align=ALIGN_CENTER_X
            )
            row["dir"] = make_label(col_dir_x, row_y, col_dir_w, row_height, "")
            row["stop"] = make_label(col_stop_x, row_y, col_stop_w, row_height, "")

            self.row_labels.append(row)
            row_y += row_height

        # Initial: nur obere Sterne sichtbar
        self.set_star_normal_pattern(top_active=True)

    # ------------------------------------------------------------------
    # Sternchen-Animation
    # ------------------------------------------------------------------
    def set_star_normal_pattern(self, top_active: bool):
        """Sekundentakt: entweder nur die oberen oder nur die unteren Sterne anzeigen."""
        if self.star_top_left is None:
            return
        self.star_top_left.setVisible(top_active)
        self.star_top_right.setVisible(top_active)
        self.star_bottom_left.setVisible(not top_active)
        self.star_bottom_right.setVisible(not top_active)

    def flash_stars_for_refresh(self, monitor):
        """Kurzes schnelles Blinken aller vier Sterne beim Refresh."""
        if self.star_top_left is None:
            return
        cycles = 6  # ergibt ca. 600–900 ms, je nach sleep
        for i in range(cycles):
            on = (i % 2 == 0)
            self.star_top_left.setVisible(on)
            self.star_top_right.setVisible(on)
            self.star_bottom_left.setVisible(on)
            self.star_bottom_right.setVisible(on)
            # kurze Pause, dabei auf Abort achten
            if monitor.waitForAbort(0.1):
                break

    # ------------------------------------------------------------------
    # API für Hauptloop
    # ------------------------------------------------------------------
    def set_update_text(self, updated):
        if updated:
            text = f"LAST UPDATE: {updated}"
        else:
            text = "LAST UPDATE: n/a"
        self.header_update_center.setLabel(text)

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
                row["del"].setLabel(delay_flag)
                row["dir"].setLabel(direction)
                row["stop"].setLabel(stop)
            else:
                row["line"].setLabel("")
                row["typ"].setLabel("")
                row["time"].setLabel("")
                row["del"].setLabel("")
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

    url = ADDON.getSetting("url") or "https://www.vrs.de/index.php?eID=tx_vrsinfo_departuremonitor&i=d8f44641a2626fa3ff5a75dd50ca2560"
    try:
        interval = int(ADDON.getSetting("refresh_interval") or "30")
    except ValueError:
        interval = 30

    log(f"Starting screensaver {ADDON_VERSION}, url={url}, interval={interval}s")

    win = ScreensaverWindow()
    win.show()

    # Phase fürs Sekundentakt-Blinken der Sterne (oben/unten)
    top_active = True

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

            # Schnell-Blinken beim Refresh
            win.flash_stars_for_refresh(monitor)

            # Header + Tabelle aktualisieren
            win.set_update_text(updated)
            win.set_data(events)

            # Countdown-Phase mit Sekundentakt-Blinken (oben/unten)
            remaining = interval
            while remaining > 0 and not monitor.abortRequested():
                win.set_countdown(remaining)
                win.set_star_normal_pattern(top_active)
                top_active = not top_active

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


if __name__ == "__main__":
    run()