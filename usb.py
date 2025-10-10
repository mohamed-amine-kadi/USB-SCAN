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

# --- Importation optionnelle des bibliothèques ---
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
    if platform.system() == "Windows":
        import wmi
        HAS_WMI = True
    else:
        HAS_WMI = False
except Exception:
    HAS_WMI = False


# --- Fonctions utilitaires ---
def now_iso():
    dt = datetime.now().astimezone()
    return dt.isoformat(), dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S"), dt.tzname()

def s(x):
    return "" if x is None else str(x)


# --- Scan avec PyUSB ---
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
            # Essai de lecture des chaînes
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


# --- Linux ---
def scan_linux():
    results = []
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

    try:
        p = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
        if p.stdout:
            for line in p.stdout.strip().splitlines():
                results.append({
                    "backend": "lsusb",
                    "line": line.strip()
                })
    except Exception:
        pass

    results.extend(scan_with_pyusb())
    return results


# --- macOS ---
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


# --- Windows ---
def scan_windows():
    results = []
    if HAS_WMI:
        try:
            c = wmi.WMI()
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

    try:
        p = subprocess.run(["wmic", "path", "Win32_USBControllerDevice", "get", "Dependent"],
                           capture_output=True, text=True, check=False)
        if p.stdout:
            results.append({"backend": "wmic_controller_device", "text": p.stdout})
    except Exception:
        pass

    results.extend(scan_with_pyusb())
    return results


# --- Dispatcher ---
def scan_all():
    system = platform.system()
    if system == "Linux":
        return scan_linux()
    elif system == "Darwin":
        return scan_macos()
    elif system == "Windows":
        return scan_windows()
    else:
        return scan_with_pyusb()


# --- Rapport HTML ---
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
  .record {{ margin-bottom: 1em; padding:8px; border-left: 4px solid #0b5394; background: #fff; }}
  pre {{ background:#f7f7f9; padding:8px; overflow:auto; }}
</style>
</head>
<body>
  <h1>USB-SCAN — Rapport</h1>
  <div class="meta">
    <strong>Date :</strong> {safe(scan_date)} &nbsp; <strong>Heure :</strong> {safe(scan_time)} &nbsp;
    <strong>Fuseau :</strong> {safe(scan_tz)}<br>
    <strong>Système :</strong> {safe(platform.system())} {safe(platform.release())}
  </div>
  <h2>Résumé : {len(scan_records)} périphérique(s) détecté(s)</h2>
  <div>
""")
    for i, rec in enumerate(scan_records, 1):
        html_parts.append(f'<div class="record"><strong>#{i} — backend: {safe(s(rec.get("backend")))}</strong><br>')
        for k in ("vendor_id","product_id","manufacturer","product","serial_number","name",
                  "device_id","pnp_device_id","service","devnode","sys_path","bus","address"):
            if k in rec and rec[k]:
                html_parts.append(f'<div><strong>{safe(k)}:</strong> {safe(s(rec[k]))}</div>')
        if "line" in rec:
            html_parts.append("<div><strong>lsusb:</strong> <code>" + safe(rec["line"]) + "</code></div>")
        if "text" in rec:
            html_parts.append("<div><strong>Sortie texte:</strong><pre>" + safe(rec["text"]) + "</pre></div>")
        if "raw" in rec:
            html_parts.append("<div><strong>Raw:</strong> <code>" + safe(rec["raw"]) + "</code></div>")
        html_parts.append("</div>")
    html_parts.append(f"""
  </div>
  <footer style="margin-top:20px; font-size:0.9rem; color:#666">
    Rapport généré le {safe(scan_time_iso)}
  </footer>
</body>
</html>
""")
    Path(filename).write_text("".join(html_parts), encoding="utf-8")
    return filename


# --- Programme principal ---
def main():
    print("="*60)
    print(" USB-SCAN — Analyse des périphériques USB ")
    print("="*60)
    print(f"Système détecté : {platform.system()} {platform.release()}")
    print("Remarque : certaines informations peuvent nécessiter des droits administrateur.\n")

    while True:
        iso, date_str, time_str, tzname = now_iso()
        print(f"Analyse en cours ({date_str} {time_str} {tzname})...")
        scan_data = scan_all()
        filename = f"usb_scan_report_{iso.replace(':', '-')}.html"
        generate_html_report(scan_data, iso, date_str, time_str, tzname, filename)
        print(f"\n✅ Analyse terminée : {len(scan_data)} périphérique(s) détecté(s).")
        print(f"📄 Rapport enregistré sous : {filename}")

        try:
            webbrowser.open(str(Path(filename).absolute().as_uri()))
            print("🌐 Ouverture du rapport dans le navigateur…")
        except Exception:
            print("⚠️ Impossible d’ouvrir le navigateur automatiquement.")

        answer = input("\nSouhaitez-vous refaire une analyse ? (o/n) : ").strip().lower()
        if answer in ("n", "no", "non"):
            print("\nMerci d’avoir utilisé USB-SCAN. À bientôt ! 👋")
            break


# --- Lancement ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n❌ Erreur inattendue :", e)
    input("\nAppuie sur Entrée pour fermer...")
