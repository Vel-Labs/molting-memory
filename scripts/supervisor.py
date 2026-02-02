#!/usr/bin/env python3
"""
Molting Memory Service Supervisor

Ensures Qdrant and memory consolidation are always running.
Designed for user-level execution (no sudo required).

Usage:
    python supervisor.py --start        # Start all services
    python supervisor.py --status       # Show status
    python supervisor.py --monitor      # Auto-restart loop (run in background)
    python supervisor.py --stop         # Stop all services

Auto-start on WSL terminal (add to ~/.bashrc):
    echo 'python3 ~/.molting-memory/supervisor.py --start' >> ~/.bashrc
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime
import requests

# Configuration
MEMORY_ROOT = Path(os.path.expanduser("~/.molting-memory"))
CONFIG = {
    "qdrant": {
        "binary": "/home/vel/qdrant",  # Adjust path for your system
        "port": 6333,
        "restart_delay": 5,
    },
    "check_interval": 60,  # seconds
}

LOG_FILE = MEMORY_ROOT / "supervisor.log"
PID_DIR = MEMORY_ROOT / "pids"
PID_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")

def get_pid(name):
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        return int(pid_file.read_text().strip())
    return None

def save_pid(name, pid):
    (PID_DIR / f"{name}.pid").write_text(str(pid))

def remove_pid(name):
    (PID_DIR / f"{name}.pid").unlink(missing_ok=True)

def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def check_qdrant():
    """Check if Qdrant is healthy."""
    try:
        resp = requests.get(f"http://127.0.0.1:{CONFIG['qdrant']['port']}/collections", timeout=2)
        return resp.status_code == 200
    except:
        return False

def start_qdrant():
    """Start Qdrant."""
    pid = get_pid("qdrant")
    if pid and is_running(pid):
        log(f"Qdrant already running (PID {pid})")
        return True
    
    qdrant_binary = CONFIG["qdrant"]["binary"]
    
    if not Path(qdrant_binary).exists():
        log(f"Qdrant binary not found: {qdrant_binary}")
        log("Download: curl -L https://qdrant.io/releases/latest/download/qdrant-x86_64-unknown-linux-musl.tar.gz | tar xz")
        return False
    
    log("Starting Qdrant...")
    try:
        proc = subprocess.Popen(
            [qdrant_binary, "--uri", f"http://127.0.0.1:{CONFIG['qdrant']['port']}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp
        )
        save_pid("qdrant", proc.pid)
        log(f"Qdrant started (PID {proc.pid})")
        
        # Wait for ready
        for i in range(10):
            time.sleep(2)
            if check_qdrant():
                log(f"Qdrant ready on port {CONFIG['qdrant']['port']}")
                return True
        log("Qdrant failed to start in time")
        return False
    except Exception as e:
        log(f"Failed to start Qdrant: {e}")
        return False

def stop_qdrant():
    pid = get_pid("qdrant")
    if not pid:
        return
    
    log(f"Stopping Qdrant (PID {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(1)
            if not is_running(pid):
                remove_pid("qdrant")
                log("Qdrant stopped")
                return
        os.kill(pid, signal.SIGKILL)
        remove_pid("qdrant")
        log("Qdrant killed")
    except OSError:
        remove_pid("qdrant")

def run_memory_brain(command):
    """Run a memory_brain.py command."""
    script = MEMORY_ROOT / "scripts" / "memory_brain.py"
    if not script.exists():
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script), command],
            capture_output=True, timeout=30
        )
        return result.returncode == 0
    except:
        return False

def status():
    """Show service status."""
    print("\n🛡️  MOLTING MEMORY STATUS")
    print("=" * 40)
    
    qdrant_ok = check_qdrant()
    qdrant_pid = get_pid("qdrant")
    
    print(f"Qdrant:      {'✅ Running' if qdrant_ok else '❌ Down'}")
    if qdrant_pid:
        print(f"  PID: {qdrant_pid}")
        print(f"  URL: http://127.0.0.1:{CONFIG['qdrant']['port']}")
    else:
        print(f"  URL: Not started")
    
    # Check memory files
    memory_dir = Path(os.path.expanduser("~/.openclaw/memory"))
    if memory_dir.exists():
        daily_files = list(memory_dir.glob("*.md"))
        print(f"\nMemory: {len(daily_files)} daily files")
    
    print()

def monitor(interval=None):
    """Monitor services with auto-restart."""
    if interval is None:
        interval = CONFIG["check_interval"]
    
    log("=" * 50)
    log("MOLTING MEMORY SUPERVISOR STARTED")
    log(f"Check interval: {interval}s")
    log("=" * 50)
    
    # Start services
    start_qdrant()
    
    while True:
        if check_qdrant():
            pid = get_pid("qdrant")
            log(f"✅ Qdrant OK (PID {pid})")
        else:
            log("❌ Qdrant down, restarting...")
            stop_qdrant()
            time.sleep(CONFIG["qdrant"]["restart_delay"])
            start_qdrant()
        
        time.sleep(interval)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Molting Memory Supervisor")
    parser.add_argument("--start", action="store_true", help="Start services")
    parser.add_argument("--stop", action="store_true", help="Stop services")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--monitor", action="store_true", help="Run monitoring loop")
    parser.add_argument("--interval", type=int, default=60, help="Check interval (seconds)")
    
    args = parser.parse_args()
    
    if args.status:
        status()
    elif args.stop:
        stop_qdrant()
        log("All services stopped")
    elif args.start:
        start_qdrant()
        status()
    elif args.monitor:
        monitor(args.interval)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
