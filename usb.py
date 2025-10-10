#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB-SCAN — Scan des périphériques USB et génération d'un rapport HTML.
Fonctionne sur Linux / Windows / macOS avec diverses méthodes (pyusb, commandes système).
"""

import sys
import platform
import subprocess
import webbrowser
import html
from datetime import datetime
from pathlib import Path

# Try to import optional libs
try:
    import usb.core
    import usb.util
    HAS_PYUSB = True
except Exception:
    HAS_PYUSB = False

try:
    import pyudev
    HAS_PYUDEV = True
except Exception:
    HAS_PYUDEV = False

try:
    # wmi works on Windows (pip install wmi)
    if platform.system() == "Windows":
        import wmi
        HAS_WMI = True
    else:
        HAS_WMI = False
except Exception:
    HAS_WMI = False

# Utility: timestamp with timezone-aware local time
def now_iso():
    dt = datetime.now().astimezone()
    return dt.isoformat(), dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S"), dt.tzname()

# Helper: safe string
def s(x):
    return "" if x is None else str(x)

# Collect info via pyusb if available (vendor/product, serial, manufacturer, product)
def scan_with_pyusb():
    results = []
    if not HAS_PYUSB:
        return results
    try:
        devices = usb.core.find(find_all=True)
        for dev in devices:
            try:
                vid = hex(dev.idVendor)
                pid = hex(dev.idProduct)
            except Exception:
                vid = s(dev.idVendor)
                pid = s(dev.idProduct)
            info = {
                "backend": "pyusb",
                "vendor_id": vid,
                "product_id": pid,
                "bus": getattr(dev, 'bus', ''),
                "address": getattr(dev, 'address', ''),
                "manufacturer": None,
                "product": None,
                "serial_number": None,
                "raw": repr(dev)
            }
            # Try to fetch strings (can fail w/o permissions)
            try:
                info["manufacturer"] = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else None
            except Exception:
                info["manufacturer"] = None
            try:
                info["product"] = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else None
            except Exception:
                info["product"] = None
            try:
                info["serial_number"] = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else None
            except Exception:
                info["serial_number"] = None
            results.append(info)
    except Exception:
        pass
    return results

# Linux: use pyudev and/or lsusb
def scan_linux():
    results = []
    # pyudev detailed enumeration (requires pyudev)
    if HAS_PYUDEV:
        try:
            ctx = pyudev.Context()
            for device in ctx.list_devices(subsystem='usb', DEVTYPE='usb_device'):
                info = {"backend": "pyudev"}
                info.update({
                    "vendor_id": device.get('ID_VENDOR_ID'),
                    "product_id": device.get('ID_MODEL_ID'),
                    "manufacturer": device.get('ID_VENDOR_FROM_DATABASE') or device.get('ID_VENDOR'),
                    "product": device.get('ID_MODEL'),
                    "serial_number": device.get('ID_SERIAL_SHORT') or device.get('ID_SERIAL'),
                    "devnode": device.device_node,
                    "sys_path": device.sys_path
                })
                results.append(info)
        except Exception:
            pass

    # fallback to lsusb (human readable). lsusb must be installed
    try:
        p = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
        if p.stdout:
            for line in p.stdout.strip().splitlines():
                # Example line: Bus 002 Device 003: ID 8087:0024 Intel Corp. Integrated Rate Matching Hub
                results.append({
                    "backend": "lsusb",
                    "line": line.strip()
                })
    except Exception:
        pass

    # add pyusb devices
    results.extend(scan_with_pyusb())
    return results

# macOS: use system_profiler SPUSBDataType
def scan_macos():
    results = []
    try:
        p = subprocess.run(["system_profiler", "SPUSBDataType", "-detailLevel", "mini"],
                           capture_output=True, text=True, check=False)
        if p.stdout:
            results.append({"backend": "system_profiler", "text": p.stdout})
    except Exception:
        pass
    results.extend(scan_with_pyusb())
    return results

# Windows: use WMI if available, otherwise wmic commands
def scan_windows():
    results = []
    if HAS_WMI:
        try:
            c = wmi.WMI()
            # Query USB PnP entities
            for dev in c.Win32_PnPEntity():
                if dev.PNPClass and "USB" in (dev.PNPClass or "") or (dev.DeviceID and "USB" in dev.DeviceID):
                    results.append({
                        "backend": "WMI",
                        "name": s(dev.Name),
                        "device_id": s(dev.DeviceID),
                        "pnp_device_id": s(dev.PNPDeviceID),
                        "manufacturer": s(dev.Manufacturer),
                        "service": s(dev.Service)
                    })
        except Exception:
            pass

    # fallback to wmic (deprecated on newer windows but often present)
    try:
        p = subprocess.run(["wmic", "path", "Win32_USBControllerDevice", "get", "Dependent"], capture_output=True, text=True, check=False)
        if p.stdout:
            results.append({"backend": "wmic_controller_device", "text": p.stdout})
    except Exception:
        pass

    # add pyusb
    results.extend(scan_with_pyusb())
    return results

# Generic scanner dispatcher
def scan_all():
    system = platform.system()
    if system == "Linux":
        return scan_linux()
    elif system == "Darwin":
        return scan_macos()
    elif system == "Windows":
        return scan_windows()
    else:
        # Other OS: try pyusb only
        return scan_with_pyusb()

# Generate HTML report for one scan
def generate_html_report(scan_records, scan_time_iso, scan_date, scan_time, scan_tz, filename):
    safe = html.escape
    html_parts = []
    html_parts.append(f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>USB-SCAN — rapport {safe(scan_time_iso)}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 20px; background:#f9f9fb; color:#222 }}
  h1 {{ color:#0b5394 }}
  .meta {{ margin-bottom: 1em; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 0 6px rgba(0,0,0,0.04) }}
  th, td {{ border: 1px solid #e2e2e2; padding: 8px; text-align:left; font-size: 0.95rem }}
  th {{ background: #f2f6fb; }}
  pre {{ background:#f7f7f9; padding:8px; overflow:auto; }}
  .record { margin-bottom: 1em; padding:8px; border-left: 4px solid #0b5394; background: #fff; }
</style>
</head>
<body>
  <h1>USB-SCAN — Rapport</h1>
  <div class="meta">
    <strong>Date :</strong> {safe(scan_date)} &nbsp; <strong>Heure :</strong> {safe(scan_time)} &nbsp; <strong>Timezone :</strong> {safe(scan_tz)}<br>
    <strong>Système :</strong> {safe(platform.system())} {safe(platform.release())} ({safe(platform.platform())})
  </div>
  <h2>Résumé des éléments trouvés : {len(scan_records)} entrées</h2>
  <div>
""")
    # For each record, render depending on its keys
    for i, rec in enumerate(scan_records, 1):
        html_parts.append(f'<div class="record"><strong>Entrée #{i} — backend: {safe(s(rec.get("backend")) )}</strong><br>')
        # Pretty print some common fields
        for k in ("vendor_id","product_id","manufacturer","product","serial_number","name","device_id","pnp_device_id","service","devnode","sys_path","bus","address"):
            if k in rec and rec[k]:
                html_parts.append(f'<div><strong>{safe(k)}:</strong> {safe(s(rec[k]))}</div>')
        # raw text or special 'line' or 'text'
        if "line" in rec:
            html_parts.append("<div><strong>lsusb line:</strong> <code>" + safe(rec["line"]) + "</code></div>")
        if "text" in rec:
            html_parts.append("<div><strong>Text output:</strong><pre>" + safe(rec["text"]) + "</pre></div>")
        if "raw" in rec:
            html_parts.append("<div><strong>raw:</strong> <code>" + safe(rec["raw"]) + "</code></div>")
        html_parts.append("</div>")  # record
    html_parts.append("""
  </div>
  <footer style="margin-top:20px; font-size:0.9rem; color:#666">
    Généré par USB-SCAN — {time_iso}
  </footer>
</body>
</html>
""".format(time_iso=safe(scan_time_iso)))
    Path(filename).write_text("".join(html_parts), encoding="utf-8")
    return filename

# Main interactive loop
def main():
    print("USB-SCAN — Analyse des ports USB et génération d'un rapport HTML.")
    print("Détection de l'OS:", platform.system())
    print("Remarque: certaines informations (serial/manufacturer) peuvent nécessiter des permissions élevées.")
    scans_done = 0
    while True:
        iso, date_str, time_str, tzname = now_iso()
        print(f"\nLancement de l'analyse — {date_str} {time_str} ({tzname}) ...")
        scan_data = scan_all()
        scans_done += 1
        # Build filename with timestamp
        safe_ts = iso.replace(":", "-")
        filename = f"usb_scan_report_{safe_ts}.html"
        outpath = generate_html_report(scan_data, iso, date_str, time_str, tzname, filename)
        print(f"Analyse terminée. {len(scan_data)} éléments trouvés.")
        print(f"Rapport écrit dans : {outpath}")
        try:
            webbrowser.open(str(Path(outpath).absolute().as_uri()))
        except Exception:
            # fallback open local path
            try:
                webbrowser.open(str(Path(outpath).absolute()))
            except Exception:
                pass

        # Demander à l'utilisateur s'il souhaite relancer
        answer = input("Souhaitez-vous faire une autre analyse ? (o/n) : ").strip().lower()
        if answer in ("n", "no", "non"):
            print("Arrêt demandé — au revoir.")
            break
        else:
            print("Nouvelle analyse demandée — relance...")

if __name__ == "__main__":
    main()
