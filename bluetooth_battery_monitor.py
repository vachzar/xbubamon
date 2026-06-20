"""
Bluetooth Battery Monitor - JARxAI
Copyright (C) 2026 by JARxAI

Features:
- Real-time battery monitoring
- Multi-device display (configurable)
- Battery notifications (30%, 20%, 10%)
"""

import sys, time, threading, subprocess, json, os
from datetime import datetime
import tkinter as tk
from tkinter import ttk

# Auto-install
for pkg, pip_name in [("pystray", "pystray"), ("PIL", "Pillow")]:
    try: __import__(pkg)
    except: subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Notification library
try:
    from plyer import notification as plyer_notification
    HAS_NOTIFICATION = True
except ImportError:
    HAS_NOTIFICATION = False

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Constants
# ============================================================
NO_WINDOW = 0x08000000
CONNECT_KEY = "{83DA6326-97A6-4088-9453-A1923F573B29} 15"
BATTERY_KEY = "{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2"
APP_NAME = "BT Battery"
COPYRIGHT = "Copyright (C) 2026 by JARxAI"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# ============================================================
# Settings Manager
# ============================================================
class SettingsManager:
    def __init__(self):
        self.data = self.load()
    
    def load(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {
                "visible_devices": [],
                "notifications_enabled": True,
                "notification_thresholds": [30, 20, 10]
            }
    
    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except: pass
    
    def get_visible_devices(self):
        return self.data.get("visible_devices", [])
    
    def set_visible_devices(self, devices):
        self.data["visible_devices"] = devices
        self.save()
    
    def is_notifications_enabled(self):
        return self.data.get("notifications_enabled", True)
    
    def get_thresholds(self):
        return self.data.get("notification_thresholds", [30, 20, 10])

# ============================================================
# Notification Manager
# ============================================================
class NotificationManager:
    def __init__(self, settings):
        self.settings = settings
        self.notified = {}
    
    def check_and_notify(self, device_name, battery_level):
        if not self.settings.is_notifications_enabled():
            return
        if battery_level is None:
            return
        
        for threshold in self.settings.get_thresholds():
            if battery_level <= threshold:
                key = f"{device_name}_{threshold}"
                if key not in self.notified:
                    self.notify(device_name, battery_level)
                    self.notified[key] = True
                    break
    def notify(self, device_name, battery_level):
        title = "Battery Low"
        msg = f"{device_name} is at {battery_level}%"
        
        # Tkinter taskbar notification (most reliable)
        self._show_taskbar_notification(title, msg)
    
    def _show_taskbar_notification(self, title, msg):
        """Show notification near taskbar, auto-close after 5s"""
        def show():
            root = tk.Tk()
            root.title(title)
            if os.path.exists(ICON_PATH):
                try:
                    root.iconbitmap(ICON_PATH)
                except: pass
            # Position near taskbar (bottom-right)
            x = root.winfo_screenwidth() - 370
            y = root.winfo_screenheight() - 180
            root.geometry(f"350x120+{x}+{y}")
            root.attributes("-topmost", True)
            root.configure(bg="#2d2d2d")
            root.overrideredirect(True)  # Remove title bar
            
            # Title
            tk.Label(root, text=title, font=("Arial", 11, "bold"), 
                     fg="#ff6b6b", bg="#2d2d2d").pack(pady=(15,5))
            
            # Message
            tk.Label(root, text=msg, font=("Arial", 10), 
                     fg="white", bg="#2d2d2d").pack(pady=5)
            
            # Auto close after 5 seconds
            root.after(5000, root.destroy)
            root.mainloop()
        
        threading.Thread(target=show, daemon=True).start()
    
    def _show_popup(self, title, msg):
        def show():
            root = tk.Tk()
            root.title(title)
            root.geometry("350x120")
            root.attributes("-topmost", True)
            root.configure(bg="#2d2d2d")
            tk.Label(root, text=title, font=("Arial", 11, "bold"), fg="#ff6b6b", bg="#2d2d2d").pack(pady=(15,5))
            tk.Label(root, text=msg, font=("Arial", 10), fg="white", bg="#2d2d2d").pack(pady=5)
            tk.Button(root, text="OK", command=root.destroy, padx=15, bg="#404040", fg="white").pack(pady=8)
            root.mainloop()
        threading.Thread(target=show, daemon=True).start()
    
    def reset(self, device_name):
        keys = [k for k in self.notified if k.startswith(device_name)]
        for key in keys:
            del self.notified[key]



# ============================================================
# PowerShell Functions
# ============================================================
def run_ps(cmd, timeout=20):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WINDOW)
        return r.stdout.strip()
    except:
        return ""

def scan_audio():
    """Scan audio devices only (fast, for display)"""
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
    return _parse_scan(run_ps(ps))

def scan_all():
    """Scan ALL Bluetooth devices (for Settings, slower)"""
    ps = """
Get-PnpDevice -Status OK | Where-Object {
    $_.InstanceId -match 'BTHENUM' -and
    $_.FriendlyName -notmatch 'Microsoft Bluetooth|RFCOMM|Protocol'
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
    
    @{Name=$name; Battery=$battery; Connected=$connected} | ConvertTo-Json -Compress
}
"""
    return _parse_scan(run_ps(ps, timeout=30))

def _parse_scan(out):
    devices = []
    if out:
        for line in out.split(chr(10)):
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                devices.append(d)
            except: pass
    return devices

# ============================================================
# Icon Drawing
# ============================================================
def make_icon(battery=None):
    """Create dynamic battery icon"""
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

# ============================================================
# Settings Window
# ============================================================
def show_settings(icon_ref, settings, on_done):
    def show():
        root = tk.Tk()
        root.title("Settings - " + APP_NAME)
        if os.path.exists(ICON_PATH):
            try:
                root.iconbitmap(ICON_PATH)
            except: pass
        root.geometry("450x400")
        root.attributes("-topmost", True)
        
        tk.Label(root, text="Device Selection", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10,5))
        tk.Label(root, text="Scanning Bluetooth devices...", fg="gray").pack(anchor="w", padx=10)
        
        list_frame = tk.Frame(root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw", tags="inner")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("inner", width=e.width))
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def do_scan():
            all_devices = scan_all()
            root.after(0, lambda: populate_list(all_devices))
        
        def populate_list(all_devices):
            for w in root.winfo_children():
                if isinstance(w, tk.Label) and "Scanning" in w.cget("text"):
                    w.destroy()
            
            tk.Label(root, text=f"Found {len(all_devices)} devices:", anchor="w").pack(anchor="w", padx=10)
            visible = settings.get_visible_devices()
            device_vars = {}
            
            for dev in all_devices:
                name = dev["Name"]
                battery = dev.get("Battery")
                connected = dev.get("Connected", False)
                var = tk.BooleanVar(root, value=(name in visible))
                device_vars[name] = var
                
                frame = tk.Frame(scrollable)
                frame.pack(fill=tk.X, pady=1)
                tk.Checkbutton(frame, text="", variable=var).pack(side=tk.LEFT)
                status = "O" if connected else "x"
                tk.Label(frame, text=status, width=2).pack(side=tk.LEFT)
                name_text = name + (f" ({battery}%)" if battery else "")
                tk.Label(frame, text=name_text, anchor="w", width=35).pack(side=tk.LEFT, fill=tk.X)
            
            def save():
                selected = [n for n, v in device_vars.items() if v.get()]
                settings.set_visible_devices(selected)
                on_done()
                root.destroy()
            
            btn_frame = tk.Frame(root)
            btn_frame.pack(fill=tk.X, padx=10, pady=10)
            tk.Button(btn_frame, text="Save", command=save, padx=20, pady=5).pack(side=tk.RIGHT, padx=5)
            tk.Button(btn_frame, text="Cancel", command=root.destroy, padx=20, pady=5).pack(side=tk.RIGHT)
        
        threading.Thread(target=do_scan, daemon=True).start()
        root.mainloop()
    threading.Thread(target=show, daemon=True).start()

# ============================================================
# Info Window
# ============================================================
def show_info(devices):
    def show():
        root = tk.Tk()
        root.title(APP_NAME + " - Info")
        if os.path.exists(ICON_PATH):
            try:
                root.iconbitmap(ICON_PATH)
            except: pass
        root.geometry("450x350")
        root.attributes("-topmost", True)
        t = tk.Text(root, wrap=tk.WORD, padx=10, pady=10, font=("Consolas",10))
        t.pack(fill=tk.BOTH, expand=True)
        lines = ["=== " + APP_NAME + " ===", ""]
        if devices:
            lines.append("Connected Devices:")
            lines.append("")
            for d in devices:
                b = str(d.get("Battery","?")) + "%" if d.get("Battery") else "N/A"
                lines.append(f"  {d['Name']}: {b}")
        else:
            lines.append("No devices found")
        lines.append("")
        lines.append(COPYRIGHT)
        t.insert(tk.END, chr(10).join(lines))
        t.config(state=tk.DISABLED)
        tk.Button(root, text="Close", command=root.destroy, padx=20, pady=5).pack(pady=8)
        root.mainloop()
    threading.Thread(target=show, daemon=True).start()

# ============================================================
# About Window
# ============================================================
def show_about():
    def show():
        root = tk.Tk()
        root.title("About")
        root.geometry("300x250")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        if os.path.exists(ICON_PATH):
            try:
                root.iconbitmap(ICON_PATH)
            except: pass
        f = tk.Frame(root, padx=20, pady=15)
        f.pack(fill=tk.BOTH, expand=True)
        
        # Icon logo
        png_path = os.path.join(BASE_DIR, "icon.png")
        if os.path.exists(png_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(png_path).resize((64, 64), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                tk.Label(f, image=photo).pack(pady=(0,10))
                f._img = photo  # Keep reference
            except Exception as e:
                print(f"Icon error: {e}")
        
        tk.Label(f, text=APP_NAME, font=("Arial",14,"bold")).pack()
        tk.Label(f, text="Bluetooth Battery Monitor").pack(pady=(5,0))
        tk.Label(f, text=COPYRIGHT, font=("Arial",9,"italic"), fg="gray").pack(pady=(10,0))
        tk.Button(f, text="Close", command=root.destroy, padx=15, pady=3).pack(pady=(10,0))
        root.mainloop()
    threading.Thread(target=show, daemon=True).start()



class App:
    def __init__(self):
        self.settings = SettingsManager()
        self.notifier = NotificationManager(self.settings)
        self.devices = []
        self.display_device = None
        self.icon = None
    
    def refresh(self):
        """Refresh display (fast - audio devices only)"""
        print("[REFRESH] Scanning audio devices...")
        self.devices = scan_audio()
        print(f"[REFRESH] Found {len(self.devices)} devices")
        for d in self.devices:
            print(f"  - {d['Name']}: Battery={d.get('Battery')}")
        
        # Get visible devices from settings
        visible = self.settings.get_visible_devices()
        
        if visible:
            # Use saved selection
            self.display_device = None
            for dev in self.devices:
                if dev["Name"] in visible and dev.get("Battery") is not None:
                    self.display_device = dev
                    break
            # Fallback: first device with battery
            if not self.display_device:
                for dev in self.devices:
                    if dev.get("Battery") is not None:
                        self.display_device = dev
                        break
        else:
            # No settings: auto-select first device with battery
            for dev in self.devices:
                if dev.get("Battery") is not None:
                    self.display_device = dev
                    self.settings.set_visible_devices([dev["Name"]])
                    break
        
        # Check notifications
        for dev in self.devices:
            if dev.get("Battery") is not None:
                self.notifier.check_and_notify(dev["Name"], dev["Battery"])
        
        self.update_icon()
    
    def update_icon(self):
        if not self.icon: return
        if self.display_device:
            b = self.display_device.get("Battery")
            self.icon.icon = make_icon(b)
            self.icon.title = self.display_device["Name"] + " | " + str(b if b else "?") + "%"
        else:
            self.icon.icon = make_icon(None)
            self.icon.title = "No device"
    
    def on_refresh(self, icon, item):
        self.refresh()
    
    def on_settings(self, icon, item):
        def on_done():
            self.refresh()
        show_settings(self.icon, self.settings, on_done)
    
    def on_info(self, icon, item):
        show_info(self.devices)
    
    def on_about(self, icon, item):
        show_about()
    
    def on_quit(self, icon, item):
        icon.stop()
    
    def run(self):
        print("Starting " + APP_NAME + "...")
        
        # Initial scan
        self.refresh()
        
        # Create menu
        menu = pystray.Menu(
            item("Refresh", self.on_refresh),
            item("Show Info", self.on_info),
            pystray.Menu.SEPARATOR,
            item("Settings...", self.on_settings),
            item("About", self.on_about),
            pystray.Menu.SEPARATOR,
            item("Quit", self.on_quit)
        )
        
        # Create icon
        if self.display_device:
            b = self.display_device.get("Battery")
            title = self.display_device["Name"] + " | " + str(b if b else "?") + "%"
        else:
            title = "No device"
            b = None
        
        icon_img = make_icon(b)
        self.icon = pystray.Icon(APP_NAME, icon_img, title=title, menu=menu)
        
        # Background poller
        def poller():
            while True:
                time.sleep(60)
                self.refresh()
        threading.Thread(target=poller, daemon=True).start()
        
        print("Running!")
        self.icon.run()

# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    App().run()
