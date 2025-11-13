# Author: Omi Shrestha
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import timedelta
from typing import Dict, Optional

from flask import Flask, jsonify, render_template_string, request

from logger import SystemLogger

app = Flask(__name__)
logger = SystemLogger()


def _read_sys_temp() -> Optional[float]:
		"""Try reading the CPU temperature from the sysfs path used on Linux/Raspberry Pi.

		Returns temperature in Celsius, or None if not available.
		"""
		path = "/sys/class/thermal/thermal_zone0/temp"
		try:
				with open(path, "r", encoding="utf8") as f:
						raw = f.read().strip()
				# file usually contains millidegrees Celsius
				temp_milli = int(raw)
				return temp_milli / 1000.0
		except Exception:
				return None


def _read_vcgencmd_temp() -> Optional[float]:
		"""Fallback: call `vcgencmd measure_temp` if available (older Pi toolchain).

		Returns temperature in Celsius, or None on failure.
		"""
		try:
				out = subprocess.check_output(["vcgencmd", "measure_temp"], stderr=subprocess.DEVNULL)
				out_str = out.decode("utf8").strip()
				# expected like: "temp=48.2'C"
				if out_str.startswith("temp="):
						val = out_str.split("=")[1].split("'")[0]
						return float(val)
		except Exception:
				return None


def get_cpu_temp_c() -> Optional[float]:
		"""Return CPU temperature in Celsius if available, otherwise None."""
		t = _read_sys_temp()
		if t is not None:
				return t
		return _read_vcgencmd_temp()


def get_ram_usage() -> Dict[str, float]:
		"""Return RAM stats (total_mb, available_mb, used_mb, used_percent).

		Uses /proc/meminfo for portability on Linux.
		"""
		meminfo = {}
		try:
				with open("/proc/meminfo", "r", encoding="utf8") as f:
						for line in f:
								parts = line.split(":")
								if len(parts) != 2:
										continue
								key = parts[0].strip()
								val = parts[1].strip().split()[0]
								meminfo[key] = int(val)  # kB
				total_kb = meminfo.get("MemTotal", 0)
				available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
				used_kb = max(total_kb - available_kb, 0)
				total_mb = total_kb / 1024.0
				available_mb = available_kb / 1024.0
				used_mb = used_kb / 1024.0
				used_percent = (used_mb / total_mb * 100.0) if total_mb > 0 else 0.0
				return {
						"total_mb": round(total_mb, 2),
						"available_mb": round(available_mb, 2),
						"used_mb": round(used_mb, 2),
						"used_percent": round(used_percent, 1),
				}
		except Exception:
				return {"total_mb": 0.0, "available_mb": 0.0, "used_mb": 0.0, "used_percent": 0.0}


def get_uptime() -> Dict[str, str]:
		"""Return uptime information (seconds, human_readable).

		Reads /proc/uptime for Linux.
		"""
		try:
				with open("/proc/uptime", "r", encoding="utf8") as f:
						raw = f.read().strip()
				secs = float(raw.split()[0])
				td = timedelta(seconds=int(secs))
				# Format as X days, HH:MM:SS
				days = td.days
				hours, remainder = divmod(td.seconds, 3600)
				minutes, seconds = divmod(remainder, 60)
				human = f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
				return {"seconds": str(int(secs)), "human": human}
		except Exception:
				return {"seconds": "0", "human": "0d 00:00:00"}


def collect_status() -> Dict[str, object]:
		"""Collect CPU temp, RAM usage and uptime into a dict ready for JSON."""
		temp = get_cpu_temp_c()
		ram = get_ram_usage()
		up = get_uptime()
		return {
				"cpu_temp_c": (round(temp, 2) if isinstance(temp, (int, float)) else None),
				"ram": ram,
				"uptime": up,
				"timestamp": int(time.time()),
		}


HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
	<head>
		<meta charset="utf-8" />
		<meta name="viewport" content="width=device-width,initial-scale=1" />
		<title>rpi-5 system information</title>
		<style>
			body { font-family: system-ui, -apple-system, Roboto, Arial; margin: 2rem; }
			.card { border: 1px solid #ddd; padding: 1rem; border-radius: 8px; max-width: 480px }
			.row { display:flex; justify-content:space-between; margin:0.5rem 0 }
			strong { color: #333 }
			.muted { color: #666 }
		</style>
	</head>
	<body>
		<h1>rpi-5 system information</h1>
		<div class="card">
			<div id="status">
				<div class="row"><div class="muted">CPU Temp</div><div id="cpu_temp">--</div></div>
				<div class="row"><div class="muted">RAM Used</div><div id="ram_used">--</div></div>
				<div class="row"><div class="muted">RAM Free</div><div id="ram_free">--</div></div>
				<div class="row"><div class="muted">Uptime</div><div id="uptime">--</div></div>
				<div class="row"><div class="muted">Last Updated</div><div id="updated">--</div></div>
			</div>
		</div>

		<script>
			async function fetchStatus(){
				try{
					const r = await fetch('/api/status');
					const j = await r.json();
					document.getElementById('cpu_temp').textContent = j.cpu_temp_c===null ? 'N/A' : j.cpu_temp_c + ' °C';
					document.getElementById('ram_used').textContent = j.ram.used_mb + ' MB (' + j.ram.used_percent + '%)';
					document.getElementById('ram_free').textContent = j.ram.available_mb + ' MB';
					document.getElementById('uptime').textContent = j.uptime.human;
					document.getElementById('updated').textContent = new Date(j.timestamp*1000).toLocaleString();
				}catch(e){
					console.error(e);
				}
			}
			fetchStatus();
			setInterval(fetchStatus, 5000);
		</script>
	</body>
</html>
"""


@app.route("/")
def index():
		return render_template_string(HTML_TEMPLATE)


@app.route("/api/status")
def api_status():
	status = collect_status()
	logger.log_metrics(status)
	return jsonify(status)


@app.route("/api/history")
def api_history():
	hours = int(request.args.get("hours", 1))
	return jsonify(logger.get_history(hours))
if __name__ == "__main__":
		# Default to listening on all interfaces so you can open from other devices on the LAN.
		# Debug disabled by default; pass FLASK_DEBUG=1 in env to enable if desired.
		app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "5000")), debug=(os.environ.get("FLASK_DEBUG")=="1"))
