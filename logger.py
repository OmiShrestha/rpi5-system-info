# Author: Omi Shrestha

"""System metrics logger for tracking temperature, RAM, and uptime history."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict


# System metrics logger
class SystemLogger:
    def __init__(self, log_dir: str = "logs", max_entries: int = 1000):
        """Initialize logger with configurable directory and max entries."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_entries = max_entries
        self.log_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
    
    def log_metrics(self, metrics: Dict) -> None:
        """Append metrics to daily log file."""
        entries = self._load_entries()
        entries.append({
            "timestamp": metrics.get("timestamp"),
            "datetime": datetime.now().isoformat(),
            "cpu_temp_c": metrics.get("cpu_temp_c"),
            "ram_used_percent": metrics.get("ram", {}).get("used_percent"),
            "ram_used_mb": metrics.get("ram", {}).get("used_mb")
        })
        
        # Keep only recent entries
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries:]
        
        self._save_entries(entries)
    
    def get_history(self, hours: int = 1) -> List[Dict]:
        """Get metrics history for the last N hours."""
        entries = self._load_entries()
        cutoff = datetime.now().timestamp() - (hours * 3600)
        return [e for e in entries if e.get("timestamp", 0) >= cutoff]
    
    def _load_entries(self) -> List[Dict]:
        """Load existing entries from log file."""
        if not self.log_file.exists():
            return []
        try:
            with open(self.log_file, "r") as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_entries(self, entries: List[Dict]) -> None:
        """Save entries to log file."""
        try:
            with open(self.log_file, "w") as f:
                json.dump(entries, f, indent=2)
        except Exception as e:
            print(f"Error saving log: {e}")
