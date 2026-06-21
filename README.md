# 🔋 XBubamon
![XBubamon Logo](logo.png)
> Bluetooth Speaker Battery Monitor for Windows System Tray

---

## 📋 Features

- ✅ **Real-time battery monitoring** untuk Bluetooth speaker/headphone
- ✅ **System tray icon** dengan level baterai (warna: hijau/kuning/merah)
- ✅ **Auto-detect** device Bluetooth yang terkoneksi
- ✅ **Smart connection check** - hanya tampilkan device yang benar-benar aktif
- ✅ **Auto-refresh** setiap 60 detik
- ✅ **Lightweight** - tanpa GUI berat, hanya icon di tray

## 🎯 Supported Devices

- Bluetooth Speaker
- Bluetooth Headphone / Headset
- Bluetooth Earbuds / Buds
- Device dengan profile A2DP / AVRCP / Handsfree

## ⚙️ Requirements

- Windows 10/11
- Python 3.8+ (untuk menjalankan dari source)
- Bluetooth adapter
- Speaker/headphone Bluetooth yang sudah pair

## 🚀 Quick Start

### Jalankan dari Source

```bash
# 1. Install dependencies
pip install pystray pillow

# 2. Jalankan
python bluetooth_battery_monitor.py
```

### Build ke EXE

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Build
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." --add-data "icon.png;." --name "BT Battery" bluetooth_battery_monitor.py

# 3. EXE ada di folder dist/
dist/BT Battery.exe
```

## 📦 Build Options

### Simple Build (Recommended — with icon)
```bash
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." --add-data "icon.png;." --name "BT Battery" bluetooth_battery_monitor.py
```

### Build tanpa Icon (no icon files required)
```bash
pyinstaller --onefile --windowed --name "BT Battery" bluetooth_battery_monitor.py
```

### Build tanpa Console Window
```bash
pyinstaller --onefile --noconsole --name "BT Battery" bluetooth_battery_monitor.py
```

### Build dengan Version Info
```bash
pyinstaller --onefile --windowed --name "BT Battery" --version-file=version.txt bluetooth_battery_monitor.py
```

## 📁 File Structure

```
bluetooth_battery_monitor/
├── bluetooth_battery_monitor.py   # Main script
├── README.md                       # This file
└── dist/
    └── BT Battery.exe             # Built executable
```

## 🔧 How It Works

### Connection Detection
Menggunakan property Windows:
```
{83DA6326-97A6-4088-9453-A1923F573B29} 15
```
Property ini return `True` jika device benar-benar connected, `False` jika disconnected.

### Battery Reading
Menggunakan property Windows:
```
{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2
```
Property ini return level baterai (0-100) dari device Bluetooth.

### Detection Flow
```
1. Scan semua device Bluetooth dengan audio profile
2. Cek connection status via property {83DA6326...}
3. Jika connected → baca battery level
4. Tampilkan di system tray
```

## 🖥️ System Tray Icon

| Icon | Arti |
|------|------|
| 🔋 Hijau (>60%) | Baterai penuh |
| 🟡 Kuning (30-60%) | Baterai sedang |
| 🔴 Merah (<30%) | Baterai rendah |
| ❓ abu-abu | Tidak ada device / battery tidak diketahui |

### Menu
- **Refresh** - Scan ulang device
- **Show Info** - Tampilkan detail device & battery
- **About** - Info aplikasi
- **Quit** - Keluar

## ❓ Troubleshooting

### "No audio device" / Icon tidak muncul
1. Pastikan speaker/headphone sudah **pair** dan **connected**
2. Cek di **Settings > Bluetooth & devices** - device harus aktif
3. Jalankan sebagai **Administrator** jika perlu

### Battery tidak terbaca (tampil "?")
1. Device mungkin tidak support battery reporting
2. Coba disconnect & reconnect device
3. Restart Bluetooth service:
   ```powershell
   Restart-Service bthserv
   ```

### Aplikasi lambat saat start
- Normal butuh ~5-7 detik untuk scan devices
- Ini karena PowerShell butuh waktu query Windows API

## 🛠️ Tech Stack

- **Python 3.10+**
- **pystray** - System tray icon
- **Pillow (PIL)** - Icon image generation
- **PowerShell** - Windows API queries
- **WMI/PnP** - Device detection

## 📝 Version History

### v1.0 (2026)
- Initial release
- Real-time battery monitoring
- Smart connection detection
- System tray integration

## 👤 Author

**JARxAI**
- Copyright (C) 2026

## 📄 License

MIT License

---

## 💡 Tips

### Run on Startup
1. Build ke EXE dulu
2. Copy EXE ke startup folder:
   ```
   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
   ```

### Create Shortcut
1. Klik kanan EXE → Create shortcut
2. Copy shortcut ke Desktop atau Start Menu

### Auto-start with Windows
```powershell
# Tambahkan ke registry (run as admin)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "BT Battery" /d "C:\Path\To\BT Battery.exe" /f
```
