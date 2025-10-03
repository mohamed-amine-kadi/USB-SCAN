import subprocess
import platform
import html
from datetime import datetime
import os
import webbrowser

def run_cmd(cmd, shell=False):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, shell=shell, timeout=60)
        output = r.stdout + ("\n" + r.stderr if r.stderr else "")
        return (r.returncode == 0, output.strip())
    except Exception as e:
        return (False, f"Erreur lors de l'exécution: {e}")

def collect_info_windows():
    cmds = [
        ("WMIC - périphériques USB", ["wmic", "usbdevice", "list", "full"]),
        ("PowerShell - Get-PnpDevice -Class USB", ["powershell", "-Command", "Get-PnpDevice -Class USB | Format-List -Property *"]),
        ("PowerShell - Get-WmiObject USBHub", ["powershell", "-Command", "Get-WmiObject Win32_USBHub | Format-List -Property *"]),
    ]
    results = []
    for desc, cmd in cmds:
        ok, out = run_cmd(cmd)
        results.append((desc, cmd, ok, out))
    return results

def collect_info_linux():
    cmds = [
        ("lsusb", ["lsusb"]),
        ("lsusb -v (détail, sudo recommandé)", ["lsusb", "-v"]),
        ("dmesg | grep -i usb", ["bash", "-lc", "dmesg | grep -i usb || true"]),
        ("lshw -class usb", ["bash", "-lc", "lshw -class usb || true"]),
        ("lsblk", ["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,VENDOR,MODEL"]),
    ]
    results = []
    for desc, cmd in cmds:
        ok, out = run_cmd(cmd, shell=cmd[0] == "bash")
        results.append((desc, cmd, ok, out))
    return results

def collect_info_macos():
    cmds = [
        ("system_profiler SPUSBDataType", ["system_profiler", "SPUSBDataType"]),
        ("ioreg -p IOUSB -l", ["ioreg", "-p", "IOUSB", "-l"]),
        ("diskutil list", ["diskutil", "list"]),
    ]
    results = []
    for desc, cmd in cmds:
        ok, out = run_cmd(cmd)
        results.append((desc, cmd, ok, out))
    return results

def build_html(report):
    now = datetime.now()
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
      <meta charset="utf-8"/>
      <title>Rapport USB - {now.strftime('%Y-%m-%d %H:%M:%S')}</title>
      <style>
        body {{ font-family: Arial; margin: 20px; }}
        h1 {{ color: #0b5; }}
        h2 {{ margin-top: 30px; }}
        pre {{ background:#f7f7f7; padding:10px; border:1px solid #ccc; white-space: pre-wrap; }}
        .ok {{ color: green; }}
        .fail {{ color: red; }}
      </style>
    </head>
    <body>
      <h1>Rapport d'information USB</h1>
      <p><strong>Date :</strong> {now.strftime('%d/%m/%Y %H:%M:%S')}</p>
      <p><strong>Système :</strong> {html.escape(platform.platform())}</p>
    """

    for section_title, entries in report.items():
        html_content += f"<h2>{html.escape(section_title)}</h2>"
        for desc, cmd, ok, out in entries:
            cmd_text = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            status = '<span class="ok">OK</span>' if ok else '<span class="fail">Échec</span>'
            html_content += f"""
            <h3>{html.escape(desc)} — {status}</h3>
            <p><strong>Commande :</strong> <code>{html.escape(cmd_text)}</code></p>
            <pre>{html.escape(out) if out else 'Aucune sortie'}</pre>
            """

    html_content += "</body></html>"
    return html_content

def main():
    os_name = platform.system()
    report = {}

    if os_name == "Windows":
        report["Informations USB - Windows"] = collect_info_windows()
    elif os_name == "Linux":
        report["Informations USB - Linux"] = collect_info_linux()
    elif os_name == "Darwin":
        report["Informations USB - macOS"] = collect_info_macos()
    else:
        report["OS non supporté"] = [("OS inconnu", ["echo", os_name], True, f"Système non reconnu : {os_name}")]

    html_result = build_html(report)

    # Sauvegarder le fichier
    fichier = "rapport_usb.html"
    with open(fichier, "w", encoding="utf-8") as f:
        f.write(html_result)

    # Ouvrir dans le navigateur
    chemin = os.path.abspath(fichier)
    webbrowser.open_new_tab(f"file://{chemin}")
    print(f"\n✔ Rapport généré : {chemin}")

    # Pause pour éviter fermeture instantanée
    input("\nAppuyez sur Entrée pour quitter...")

if __name__ == "__main__":
    main()
