# Analysis - Request Review

## User Request
"Scan semua device connected hanya ketika menu settings.
Pertahankan state yang sekarang untuk langsung menampilkan 1 device saja kecuali sudah ada setting yang tersimpan."

---

## Understanding

### Current Behavior (what we have now)
```
App Start -> Scan audio devices -> Show 1st device with battery
```
- Fast (~5s)
- Simple
- Shows 1 device only

### Requested Behavior
```
App Start -> Scan audio devices -> Show 1 device (like now)
                |
        If settings exist -> Show selected devices
                |
Open Settings -> Scan ALL BT devices -> Show list for selection
                |
Save Settings -> Apply selection -> Show selected devices
```

---

## Key Insight

**Scan ALL devices = ONLY when Settings opened**

Why this is smart:
1. Fast startup (only scan audio devices, not ALL BT)
2. Settings scan is expected (user waits anyway)
3. Saves battery/CPU (no unnecessary scanning)
4. Clean separation: display vs configuration

---

## Implementation Plan

### State Management

```
App State:
- self.all_devices = []      # Current scan
- self.settings = {
    visible_devices: [],     # User selection
}
```

### Flow Diagram

```
START
  |
  +-- Load settings from JSON
  |
  +-- IF settings.visible_devices exists:
  |     +-- Scan only those devices
  |        +-- Show them
  |
  +-- ELSE (no settings):
        +-- Scan audio devices
           +-- Show 1st with battery
           +-- Auto-save to settings
```

### Settings Flow

```
User clicks "Settings..."
  |
  +-- Scan ALL Bluetooth devices (takes ~7s)
  |
  +-- Show Settings window with device list
  |
  +-- User clicks Save
       +-- Save to settings JSON
       +-- Refresh display
```

---

## Scan Types Comparison

| Type | When | Speed | Scope |
|------|------|-------|-------|
| Display scan | Every 60s | ~5s | Audio only (fast) |
| Settings scan | On Settings click | ~7s | ALL BT devices |

---

## Benefits of This Approach

1. **Fast startup** - No unnecessary scanning
2. **Simple default** - Shows 1 device, no config needed
3. **Power user friendly** - Can configure via Settings
4. **Resource efficient** - Only scan ALL when requested
5. **Clean UX** - Settings shows "Scanning..." feedback

---

## Edge Cases

1. **No devices connected** - Show "No device" icon
2. **Settings device disconnected** - Fall back to "No device", keep settings
3. **Multiple devices, none selected** - Show first audio device, auto-save

---

## Summary

The request is well-designed:
- Maintains current simple behavior
- Adds power-user features via Settings
- Efficient resource usage
- Clean separation of concerns

Ready to implement!
