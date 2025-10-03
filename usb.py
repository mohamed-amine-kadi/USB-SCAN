#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import platform
import html
from datetime import datetime
import os
import webbrowser

def run_cmd(cmd, shell=False):
    """Exécute une commande et retourne (success, stdout+stderr)."""
    try:
        # si cmd est une liste, shell=False est préférable
        r = subprocess.run(cmd, capture_output=True, text=True, shell=shell, timeout=60)
        output = r.stdout + ("\n" + r.stderr if r.stderr else "")
        return (r.returncode == 0, output.strip())
    except Exception as e:
        return (False, f"Erreur lors de l'exécution: {e}")

def collect_info_windows():
    cmds = [
        # commandes WMIC / PowerShell pour info USB
        ("WMIC : liste des périphériques USB (relation controllers -> devices)",
         ["wmic", "path", "Win32_USBControllerDevice", "get", "Dependent"]),
        ("WMIC : détails des périphériques USB",
         ["wmic", "usbdevice", "list", "full"]),
        ("PowerShell : PnP devices de classe USB (plus moderne)",
         ["powershell", "-Command", "Get-PnpDevice -Class USB | Format-List -Property *"]),
        ("PowerShell : infos détaillées WMI pour hubs USB",
         ["powershell", "-Command", "Get-WmiObject Win32_USBHub | Format-List -Property *"]),
        # Tentative d'obtenir propriétés PnP si disponibles
        ("PowerShell : propriétés PnP (peut nécessiter admin)",
         ["powershell", "-Command", "Get-PnpDeviceProperty -InstanceId (Get-PnpDevice -Class USB).InstanceId | Format-List -Property *"])
    ]
    results = []
    for desc, cmd in cmds:
        ok, out = run_cmd(cmd)
        results.append((desc, cmd, ok, out))
    return results

def collect_info_linux():
    cmds = [
        ("lsusb (résumé)", ["lsusb"]),
        ("lsusb -v (détails) — peut nécessiter sudo", ["lsusb", "-v"]),
        ("dmesg | grep -i usb (messages noyau)", ["bash", "-lc", "dmesg | grep -i usb || true"]),
        ("lshw -class usb (détails matériels) — peut nécessiter sudo", ["bash", "-]()
