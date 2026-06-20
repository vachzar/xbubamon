# Feature Plan - BT Battery Monitor

## Multi-device Display & Battery Notifications

**Author:** JARxAI  
**Date:** June 2026

---

## Feature 1: Multi-device Display

### Goal
Show multiple connected Bluetooth devices with user selection via Settings.

### Architecture

```
System Tray Icon
├── Hover → Show all selected devices
├── Menu
│   ├── Refresh
│   ├── Show Info
│   ├── Settings... ← NEW
│   ├── About
│   └── Quit
```

### Implementation Steps

1. Update scan_devices() - return all connected devices
2. Create DeviceManager class - manage device list & visibility
3. Update draw_icon() - show average battery for multiple devices
4. Update tooltip - show all selected devices
5. Create Settings window - checkboxes for device selection
6. Update tray menu - add Settings option

### Settings Storage

```json
{
  "visible_devices": ["Play 2", "JBL Flip"],
  "show_all_by_default": false
}
```

### UI Design

Settings Window:
```
Settings
├── Devices to display:
│   ├── [x] Play 2 (50%)
│   ├── [x] JBL Flip (80%)
│   └── [ ] Galaxy Buds (65%)
├── [Save] [Cancel]
```

---

## Feature 2: Battery Notifications

### Goal
Windows notification when battery reaches 30%, 20%, 10%.

### Implementation

Using winotify (Windows 10/11 native):

```python
from winotify import Notification

def notify_battery(device_name, battery_level):
    toast = Notification(
        app_id="BT Battery Monitor",
        title="Battery Low",
        msg=f"{device_name} is at {battery_level}%",
        duration="long"
    )
    toast.show()
```

### Logic

- Track notified thresholds per device
- Only notify once per threshold
- Reset after charging above threshold

### Settings

```json
{
  "notifications_enabled": true,
  "notification_thresholds": [30, 20, 10]
}
```

---

## File Changes

- bluetooth_battery_monitor.py - Add DeviceManager, NotificationManager, Settings window

## Dependencies

- pip install winotify

## Testing

- Multi-device: toggle visibility, settings persist
- Notifications: at 30%, 20%, 10% - no duplicates

---

Plan by JARxAI | June 2026
