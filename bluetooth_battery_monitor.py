"""
Bluetooth Battery Monitor - JARxAI
Copyright (C) 2026 by JARxAI
"""

import sys, time, threading, subprocess, json, os
from datetime import datetime
import tkinter as tk

# Auto-install
for pkg, pip_name in [("pystray", "pystray"), ("PIL", "Pillow")]:
    try: __import__(pkg)
    except: subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont

NO_WINDOW = 0x08000000
CONNECT_KEY = "{83DA6326-97A6-4088-9453-A1923F573B29} 15"
BATTERY_KEY = "{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2"
APP_NAME = "BT Battery"
COPYRIGHT = "Copyright (C) 2026 by JARxAI"

def run_ps(cmd, timeout=20):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WINDOW)
        return r.stdout.strip()
    except:
        return ""

def scan():
    """Get audio devices with battery"""
    ps = """
Get-PnpDevice -Status OK | Where-Object {
    $_.InstanceId -match 'BTHENUM' -and
    $_.FriendlyName -match 'Audio|Speaker|Headphone|Headset|Buds|Sound|A2DP|AVRCP|Handsfree'
} | Select-Object -ExpandProperty FriendlyName -Unique | ForEach-Object {
    $name = $_
    $base = $name -replace ' Avrcp Transport','' -replace ' Hands-Free','' -replace ' Handsfree','' -replace ' Headset','' -replace ' Headphones','' -replace ' \(','' -replace '\)',''
    
    $connected = $false
    Get-PnpDevice -Status OK -FriendlyName "*$base*" | Where-Object { $_.InstanceId -match 'BTHENUM' } | ForEach-Object {
        $c = $_ | Get-PnpDeviceProperty -KeyName '""" + CONNECT_KEY + """' -ErrorAction SilentlyContinue
        if ($c -and [bool]$c.Data) { $connected = $true }
    }
    
    $battery = $null
    if ($connected) {
        $b = Get-PnpDevice -Status OK -FriendlyName "*$base*" | ForEach-Object {
            $t = $_ | Get-PnpDeviceProperty -KeyName '""" + BATTERY_KEY + """' -ErrorAction SilentlyContinue | Where Type -ne Empty
            if ($t) { $t.Data }
        } | Select-Object -First 1
        if ($b) { $battery = [int]$b }
    }
    
    @{Name=$name; Battery=$battery} | ConvertTo-Json -Compress
}
"""
    out = run_ps(ps)
    devices = []
    if out:
        for line in out.split(chr(10)):
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                if d.get("Battery") is not None:
                    devices.append(d)
            except: pass
    return devices

def make_icon(battery=None):
    """Create icon"""
    img = Image.new("RGBA", (64, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    if battery is None:
        d.ellipse([8,8,56,56], fill=(80,80,80))
        d.line([(20,20),(44,44)], fill="red", width=4)
        d.line([(44,20),(20,44)], fill="red", width=4)
    else:
        bx,by,bw,bh = 10,16,38,32
        d.rectangle([bx,by,bx+bw,by+bh], outline="white", width=2)
        d.rectangle([bx+bw,by+8,bx+bw+5,by+bh-8], outline="white", fill="white")
        c = (0,200,0) if battery > 60 else (255,200,0) if battery > 30 else (255,50,50)
        fw = int((bw-6)*min(battery,100)/100)
        d.rectangle([bx+3,by+3,bx+3+fw,by+bh-3], fill=c)
        try: f = ImageFont.truetype("arial.ttf", 14)
        except: f = ImageFont.load_default()
        t = str(battery)+"%"
        bb = d.textbbox((0,0), t, font=f)
        d.text((bx+(bw-bb[2]+bb[0])//2, by+(bh-bb[3]+bb[1])//2), t, fill="white", font=f)
    try: fs = ImageFont.truetype("arial.ttf", 10)
    except: fs = ImageFont.load_default()
    d.text((22,2), "BT", fill="cyan", font=fs)
    return img

# Global state
devices = []
main_device = None

def do_scan():
    global devices, main_device
    devices = scan()
    main_device = devices[0] if devices else None

def on_refresh(icon, item):
    global devices, main_device
    do_scan()
    if main_device:
        icon.icon = make_icon(main_device.get("Battery"))
        icon.title = main_device["Name"] + " | " + str(main_device.get("Battery","?")) + "%"
    else:
        icon.icon = make_icon(None)
        icon.title = "No device"

def on_info(icon, item):
    def show():
        root = tk.Tk()
        root.title("BT Battery Info")
        root.geometry("400x300")
        root.attributes("-topmost", True)
        t = tk.Text(root, wrap=tk.WORD, padx=10, pady=10, font=("Consolas",10))
        t.pack(fill=tk.BOTH, expand=True)
        lines = ["=== BT Battery Monitor ===", ""]
        if devices:
            for d in devices:
                lines.append(d["Name"] + ": " + str(d.get("Battery","?")) + "%")
        else:
            lines.append("No devices found")
        lines.append("")
        lines.append(COPYRIGHT)
        t.insert(tk.END, chr(10).join(lines))
        t.config(state=tk.DISABLED)
        tk.Button(root, text="Close", command=root.destroy, padx=20, pady=5).pack(pady=8)
        root.mainloop()
    threading.Thread(target=show, daemon=True).start()

def on_about(icon, item):
    def show():
        root = tk.Tk()
        root.title("About")
        root.geometry("300x180")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        f = tk.Frame(root, padx=20, pady=15)
        f.pack(fill=tk.BOTH, expand=True)
        tk.Label(f, text=APP_NAME, font=("Arial",14,"bold")).pack()
        tk.Label(f, text="Bluetooth Battery Monitor").pack(pady=(5,0))
        tk.Label(f, text=COPYRIGHT, font=("Arial",9,"italic"), fg="gray").pack(pady=(10,0))
        tk.Button(f, text="Close", command=root.destroy, padx=15, pady=3).pack(pady=(10,0))
        root.mainloop()
    threading.Thread(target=show, daemon=True).start()

def on_quit(icon, item):
    icon.stop()

def main():
    print("Starting " + APP_NAME + "...")
    do_scan()
    
    if main_device:
        title = main_device["Name"] + " | " + str(main_device.get("Battery","?")) + "%"
        icon_img = make_icon(main_device.get("Battery"))
    else:
        title = "No device"
        icon_img = make_icon(None)
    
    menu = pystray.Menu(
        item("Refresh", on_refresh),
        item("Show Info", on_info),
        pystray.Menu.SEPARATOR,
        item("About", on_about),
        pystray.Menu.SEPARATOR,
        item("Quit", on_quit)
    )
    
    icon = pystray.Icon(APP_NAME, icon_img, title=title, menu=menu)
    
    def poller():
        while True:
            time.sleep(60)
            on_refresh(icon, None)
    threading.Thread(target=poller, daemon=True).start()
    
    print("Running!")
    icon.run()

if __name__ == "__main__":
    main()
