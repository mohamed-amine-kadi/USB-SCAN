#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
USB-SCAN — Scan des périphériques USB et génération d'un rapport HTML enrichi.
Ajout : saisie de l'utilisateur, date/heure, poste, et affichage en tableau.
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
    if platform.system() == "Windows":
        import wmi
        HAS_WMI = True
    else:
        HAS_WMI = False
except Exception:
    HAS_WMI = False


def now_iso():
    dt = datetime.now().astimezone()
    return dt.isoformat(), dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S"), dt.tzname()


def s(x):
    return "" if x is None else str(x)


def scan_with_pyusb():
    results = []
    if not HAS_PYUSB:
        return results
    try:
        devices = usb.core.find(find_all=True)
        for dev in devices:
            info = {
                "backend": "pyusb",
                "vendor_id": hex(dev.idVendor) if hasattr(dev, "idVendor") else "",
                "product_id": hex(dev.idProduct) if hasattr(dev, "idProduct") else "",
                "bus": getattr(dev, "bus", ""),
                "address": getattr(dev, "address", ""),
                "manufacturer": None,
                "product": None,
                "serial_number": None,
            }
            try:
                info["manufacturer"] = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else None
            except Exception:
                pass
            try:
                info["product"] = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else None
            except Exception:
                pass
            try:
                info["serial_number"] = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else None
            except Exception:
                pass
            results.append(info)
    except Exception:
        pass
    return results


def scan_linux():
    results = []
    if HAS_PYUDEV:
        try:
            ctx = pyudev.Context()
            for device in ctx.list_devices(subsystem="usb", DEVTYPE="usb_device"):
                info = {
                    "backend": "pyudev",
                    "vendor_id": device.get("ID_VENDOR_ID"),
                    "product_id": device.get("ID_MODEL_ID"),
                    "manufacturer": device.get("ID_VENDOR_FROM_DATABASE") or device.get("ID_VENDOR"),
                    "product": device.get("ID_MODEL"),
                    "serial_number": device.get("ID_SERIAL_SHORT") or device.get("ID_SERIAL"),
                }
                results.append(info)
        except Exception:
            pass

    try:
        p = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
        if p.stdout:
            for line in p.stdout.strip().splitlines():
                results.append({"backend": "lsusb", "line": line.strip()})
    except Exception:
        pass

    results.extend(scan_with_pyusb())
    return results


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


def scan_windows():
    results = []
    if HAS_WMI:
        try:
            c = wmi.WMI()
            for dev in c.Win32_PnPEntity():
                print("test USB")
                if dev.PNPClass and "USB" in (dev.PNPClass or ""):
                    results.append({
                        "backend": "WMI",
                        "name": s(dev.Name),
                        "device_id": s(dev.DeviceID),
                        "manufacturer": s(dev.Manufacturer)
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


def generate_html_report(scan_records, info_user, filename):
    safe = html.escape

    html_head = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>USB-SCAN — Rapport</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f6fa; color: #222; }}
h1 {{ color: #0b5394; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
th {{ background-color: #dbe9ff; }}
.meta {{ background: #fff; padding: 10px; border: 1px solid #ccc; margin-bottom: 20px; }}
footer {{ margin-top: 20px; font-size: 0.9rem; color: #666; text-align: center; }}
</style>
</head>
<body>
<h1>Rapport d’analyse USB</h1>

<div class="meta">
<strong>Nom :</strong> {safe(info_user['nom'])} {safe(info_user['prenom'])}<br>
<strong>Poste :</strong> {safe(info_user['poste'])}<br>
<strong>Date :</strong> {safe(info_user['date'])}<br>
<strong>Heure :</strong> {safe(info_user['heure'])}<br>
<strong>OS :</strong> {safe(platform.system())} {safe(platform.release())}<br>
<strong>Ports USB détectés :</strong> {len(scan_records)}
</div>

<table>
<thead>
<tr>
<th>#</th>
<th>Backend</th>
<th>Fabricant</th>
<th>Produit</th>
<th>Numéro de série</th>
<th>Vendor ID</th>
<th>Product ID</th>
</tr>
</thead>
<tbody>
"""

    rows = ""
    for i, rec in enumerate(scan_records, 1):
        rows += f"""
<tr>
<td>{i}</td>
<td>{safe(s(rec.get('backend')))}</td>
<td>{safe(s(rec.get('manufacturer')))}</td>
<td>{safe(s(rec.get('product')))}</td>
<td>{safe(s(rec.get('serial_number')))}</td>
<td>{safe(s(rec.get('vendor_id')))}</td>
<td>{safe(s(rec.get('product_id')))}</td>
</tr>
"""

    html_end = f"""
</tbody>
</table>
<footer>
Généré automatiquement le {safe(info_user['date'])} à {safe(info_user['heure'])}.
</footer>
</body>
</html>
"""

    Path(filename).write_text(html_head + rows + html_end, encoding="utf-8")
    return filename


def main():
    print("=== USB-SCAN — Rapport d'analyse USB ===\n")

    nom = input("Nom de l'utilisateur : ").strip()
    prenom = input("Prénom de l'utilisateur : ").strip()
    poste = input("Nom ou numéro du poste : ").strip()
    iso, date_str, time_str, tzname = now_iso()

    print("\nAnalyse en cours, veuillez patienter...\n")
    scan_data = scan_all()

    info_user = {
        "nom": nom,
        "prenom": prenom,
        "poste": poste,
        "date": date_str,
        "heure": time_str,
    }

    safe_ts = iso.replace(":", "-")
    filename = f"usb_scan_report_{safe_ts}.html"
    outpath = generate_html_report(scan_data, info_user, filename)

    print(f"Analyse terminée. {len(scan_data)} ports USB détectés.")
    print(f"Rapport généré : {outpath}")
    webbrowser.open(str(Path(outpath).absolute().as_uri()))

    input("\nAppuyez sur Entrée pour fermer le programme...")


if __name__ == "__main__":
    main()
