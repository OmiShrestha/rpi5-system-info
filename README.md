# rpi-5 system information dashboard

This is a small project that shows a minimal dashboard for a Raspberry Pi (rpi-5) system information: CPU temperature, RAM usage, and Uptime.

It demonstrates simple file I/O (/proc and /sys), a subprocess fallback, and a tiny Flask web server.

Files
- `system-info.py` - Flask app + functions to collect system info.
- `requirements.txt` - minimal dependency list.

Quick start

1. (Optional) create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python system-info.py
```

4. Open a browser on the Pi or another machine on the same LAN to:

    http://<pi-ip>:5000/

Notes and learning points
- CPU temperature: tries `/sys/class/thermal/thermal_zone0/temp` first (millidegrees Celsius). Falls back to `vcgencmd measure_temp` if available.
- RAM: reads `/proc/meminfo` and computes used/free in MB and percent.
- Uptime: reads `/proc/uptime` and formats a simple human-readable string.
- The app provides both an HTML dashboard and a JSON endpoint at `/api/status` for programmatic use.

Next steps you might try
- Add graphs using Chart.js and a small history buffer in memory.
- Add authentication if exposing publicly.
- Add unit tests for the parsing functions by mocking `/proc/meminfo` and `/proc/uptime`.
