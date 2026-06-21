"""
Bluetooth Battery Monitor - JARxAI
Copyright (C) 2026 by JARxAI

Features:
- Real-time battery monitoring
- Multi-device display (configurable)
- Battery notifications (30%, 20%, 10%)
"""

import sys, time, threading, subprocess, json, os, logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import queue

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("XBubamon")

# Notification library
try:
    from plyer import notification as plyer_notification
    HAS_NOTIFICATION = True
except ImportError:
    HAS_NOTIFICATION = False

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont

# Tkinter queue for thread-safe window creation
_tk_queue = queue.Queue()
_tk_root_ref = [None]

def _tk_processor():
    """Run Tk mainloop in a dedicated thread, processing queued windows."""
    def process_queue():
        while True:
            try:
                func = _tk_queue.get_nowait()
                func()
            except queue.Empty:
                break
        root.after(100, process_queue)

    root = tk.Tk()
    root.withdraw()
    _tk_root_ref[0] = root
    root.after(100, process_queue)
    root.mainloop()

def _tk_run(func):
    """Enqueue a window-building function to run on the Tk thread."""
    _tk_queue.put(func)

# Embed icon for PyInstaller
def resource_path(relative_path):
    """Get absolute path to resource"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ============================================================
# Constants
# ============================================================
NO_WINDOW = 0x08000000
CONNECT_KEY = "{83DA6326-97A6-4088-9453-A1923F573B29} 15"
BATTERY_KEY = "{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2"
VERSION = "0.1.0"
APP_NAME = "XBubamon" + " v" + VERSION
COPYRIGHT = "Copyright (C) 2026 by JARxAI"
ICON_PATH = resource_path("icon.ico")
ICON_PNG_PATH = resource_path("logo.png")
SETTINGS_FILE = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'BT Battery', 'settings.json')

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
        except (FileNotFoundError, json.JSONDecodeError) as e:
            L = "Settings load failed: " + str(e)
            logger.warning(L)
            return {
                "visible_devices": [],
                "notifications_enabled": True,
                "notification_thresholds": [30, 20, 10]
            }
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            # Atomic write: write to temp file, then rename
            tmp = SETTINGS_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, SETTINGS_FILE)
        except (OSError, IOError) as e:
            L = "Failed to save settings: " + str(e)
            logger.error(L)
    
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
        self._lock = threading.Lock()
    
    def check_and_notify(self, device_name, battery_level):
        if not self.settings.is_notifications_enabled():
            return
        if battery_level is None:
            return
        
        for threshold in self.settings.get_thresholds():
            if battery_level <= threshold:
                key = f"{device_name}_{threshold}"
                with self._lock:
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
                except Exception as e:
                    L = "Icon not available: " + str(e)
                    logger.warning(L)
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
        
        _tk_run(show)
    
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
        _tk_run(show)
    
    def reset(self, device_name):
        with self._lock:
            keys = [k for k in self.notified if k.startswith(device_name)]
            for key in keys:
                del self.notified[key]

    def cleanup_notified(self, max_entries=100):
        """Prevent unbounded growth of notified dict."""
        with self._lock:
            if len(self.notified) > max_entries:
                excess = len(self.notified) - 50
                for key in list(self.notified.keys())[:excess]:
                    del self.notified[key]


# ============================================================
# PowerShell Functions
# ============================================================
def run_ps(cmd, timeout=45):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           creationflags=NO_WINDOW)
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as e:
        L = "PowerShell command failed: " + str(e)
        logger.warning(L)
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
            except (json.JSONDecodeError, KeyError) as e:
                L = "Parse error: " + str(e)
                logger.warning(L)
    return devices

# ============================================================
# Icon Drawing
# ============================================================
def make_icon(battery=None):
    """Create squary icon with dragon head"""
    img = Image.new("RGBA", (64, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    
    if battery is None:
        # Disconnected - dragon with red X
        # Square battery body (gray)
        bx, by, bw, bh = 4, 4, 56, 56
        d.rectangle([bx, by, bx+bw, by+bh], fill=(40,40,40), outline=(80,80,80), width=2)
        
        # Battery tip
        d.rectangle([bx+20, by-4, bx+36, by+2], fill=(60,60,60), outline=(80,80,80))
        
        # Red X (BEHIND dragon)
        x_color = (255, 50, 50)
        x_width = 5
        d.line([(12, 12), (52, 52)], fill=x_color, width=x_width)
        d.line([(52, 12), (12, 52)], fill=x_color, width=x_width)
        
        # Dragon head - centered and lower (dy=22)
        dragon_color = (255, 255, 255)
        dx, dy = 19, 22
        
        # Trapezoid body
        points = [
            (dx, dy),
            (dx+26, dy),
            (dx+22, dy+18),
            (dx+4, dy+18)
        ]
        d.polygon(points, fill=dragon_color, outline=(200,200,200))
        
        # Horns - pointing UP (white)
        d.polygon([(dx+2, dy+2), (dx+8, dy+2), (dx+5, dy-6)], fill=dragon_color)
        d.polygon([(dx+18, dy+2), (dx+24, dy+2), (dx+21, dy-6)], fill=dragon_color)
        
        # Eyes (black)
        d.rectangle([dx+6, dy+5, dx+10, dy+9], fill=(0,0,0))
        d.rectangle([dx+16, dy+5, dx+20, dy+9], fill=(0,0,0))
        
        # Nose
        d.rectangle([dx+8, dy+13, dx+18, dy+16], fill=dragon_color)
        d.rectangle([dx+10, dy+14, dx+12, dy+16], fill=(0,0,0))
        d.rectangle([dx+16, dy+14, dx+18, dy+16], fill=(0,0,0))
        
        return img


    
    # Square battery body
    bx, by, bw, bh = 4, 4, 56, 56
    d.rectangle([bx, by, bx+bw, by+bh], fill=(30,30,30), outline=(80,80,80), width=2)
    
    # Battery tip (top)
    d.rectangle([bx+20, by-4, bx+36, by+2], fill=(80,80,80), outline=(100,100,100))
    
    # Battery fill (from bottom up)
    c = (0, 200, 0) if battery > 60 else (255, 200, 0) if battery > 30 else (255, 50, 50)
    fill_height = int((bh-8) * min(battery, 100) / 100)
    d.rectangle([bx+4, by+bh-4-fill_height, bx+bw-4, by+bh-4], fill=c)
    
    # Dragon head - trapezoid
    dragon_color = (255, 255, 255) if battery > 50 else (200, 200, 200)
    dx, dy = bx+14, by+12
    
    # Trapezoid body
    points = [
        (dx, dy),
        (dx+26, dy),
        (dx+22, dy+16),
        (dx+4, dy+16)
    ]
    d.polygon(points, fill=dragon_color, outline=(150,150,150))
    
    # Horns - pointing UP
    d.polygon([(dx+2, dy+2), (dx+8, dy+2), (dx+5, dy-6)], fill=dragon_color)
    d.polygon([(dx+18, dy+2), (dx+24, dy+2), (dx+21, dy-6)], fill=dragon_color)
    
    # Eyes
    d.rectangle([dx+6, dy+4, dx+10, dy+8], fill=(0,0,0))
    d.rectangle([dx+16, dy+4, dx+20, dy+8], fill=(0,0,0))
    
    # Nose
    d.rectangle([dx+8, dy+12, dx+18, dy+15], fill=dragon_color)
    d.rectangle([dx+10, dy+13, dx+12, dy+15], fill=(0,0,0))
    d.rectangle([dx+16, dy+13, dx+18, dy+15], fill=(0,0,0))
    
    # Battery percentage text
    try: f = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        f = ImageFont.load_default()
    t = str(battery) + "%"
    bb = d.textbbox((0,0), t, font=f)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    d.text((bx+(bw-tw)//2, by+bh-18), t, fill="white", font=f)
    
    return img

def show_settings(icon_ref, settings, on_done):
    def show():
        # Scan devices FIRST (synchronous, takes ~5-7s)
        all_devices = scan_all()
        
        # Then create window
        root = tk.Tk()
        root.title("Settings - " + APP_NAME)
        if os.path.exists(ICON_PATH):
            try: root.iconbitmap(ICON_PATH)
            except Exception as e:
                L = "Icon not available: " + str(e)
                logger.warning(L)
        root.geometry("450x400")
        root.attributes("-topmost", True)
        
        tk.Label(root, text="Device Selection", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10,5))
        tk.Label(root, text=f"Found {len(all_devices)} devices:", anchor="w").pack(anchor="w", padx=10)
        
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
        
        root.mainloop()
    
    _tk_run(show)

def show_info(devices):
    def show():
        root = tk.Tk()
        root.title(APP_NAME + " - Info")
        if os.path.exists(ICON_PATH):
            try:
                root.iconbitmap(ICON_PATH)
            except Exception as e:
                L = "Icon not available: " + str(e)
                logger.warning(L)
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
    _tk_run(show)

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
            except Exception as e:
                L = "Icon not available: " + str(e)
                logger.warning(L)
        f = tk.Frame(root, padx=20, pady=15)
        f.pack(fill=tk.BOTH, expand=True)
        
        # Icon logo
        png_path = ICON_PNG_PATH
        if os.path.exists(png_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(png_path).resize((64, 64), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                tk.Label(f, image=photo).pack(pady=(0,10))
                f._img = photo  # Keep reference
            except Exception as e:
                L = "Icon error: " + str(e)
                logger.warning(L)
        
        tk.Label(f, text=APP_NAME, font=("Arial",14,"bold")).pack()
        tk.Label(f, text="Bluetooth Battery Monitor").pack(pady=(5,0))
        tk.Label(f, text=COPYRIGHT, font=("Arial",9,"italic"), fg="gray").pack(pady=(10,0))
        tk.Button(f, text="Close", command=root.destroy, padx=15, pady=3).pack(pady=(10,0))
        root.mainloop()
    _tk_run(show)



class App:
    def __init__(self):
        self.settings = SettingsManager()
        self.notifier = NotificationManager(self.settings)
        self.devices = []
        self.display_device = None
        self.icon = None
        self._lock = threading.Lock()
    
    def refresh(self):
        """Refresh display (fast - audio devices only)"""
        logger.info("Scanning audio devices...")
        new_devices = scan_audio()
        logger.info(f"Found {len(new_devices)} devices")

        # Get visible devices from settings
        visible = self.settings.get_visible_devices()
        display_device = None

        if visible:
            for dev in new_devices:
                if dev["Name"] in visible and dev.get("Battery") is not None:
                    display_device = dev
                    break
            if not display_device:
                for dev in new_devices:
                    if dev.get("Battery") is not None:
                        display_device = dev
                        break
        else:
            for dev in new_devices:
                if dev.get("Battery") is not None:
                    display_device = dev
                    self.settings.set_visible_devices([dev["Name"]])
                    break

        # Lock: update shared state atomically
        with self._lock:
            self.devices = new_devices
            self.display_device = display_device

        # Notifications (uses its own lock)
        for dev in new_devices:
            if dev.get("Battery") is not None:
                self.notifier.check_and_notify(dev["Name"], dev["Battery"])
        self.notifier.cleanup_notified()

        self.update_icon()

    def update_icon(self):
        if not self.icon:
            return
        with self._lock:
            if self.display_device:
                b = self.display_device.get("Battery")
                new_icon = make_icon(b)
                title = self.display_device["Name"] + " | " + str(b if b else "?") + "%"
            else:
                new_icon = make_icon(None)
                title = "No device"
        self.icon.icon = new_icon
        self.icon.title = title
        try:
            self.icon.update_icon()
        except Exception as e:
            logger.warning(f"Icon update failed: {e}")

    def on_refresh(self, icon, item):
        self.refresh()
    
    def on_settings(self, icon, item):
        def on_done():
            self.refresh()
        show_settings(self.icon, self.settings, on_done)
    
    def on_info(self, icon, item):
        with self._lock:
            devs = list(self.devices)
        show_info(devs)
    
    def on_about(self, icon, item):
        show_about()
    
    def on_quit(self, icon, item):
        icon.stop()
    
    def run(self):
        logger.info("Starting " + APP_NAME + "...")
        
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
        
        logger.info("Running!")
        self.icon.run()

# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    # Start Tk processor in background
    threading.Thread(target=_tk_processor, daemon=True).start()
    time.sleep(0.3)  # let Tk root initialize
    App().run()
