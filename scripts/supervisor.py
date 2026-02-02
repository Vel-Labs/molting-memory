#!/usr/bin/env python3
"""
Molting Memory Service Supervisor

Ensures Qdrant and memory consolidation are always running.
Designed for user-level execution (no sudo required).

Environment Variables (optional):
    MOLTING_MEMORY_DIR  - Installation directory (~/.molting-memory)
    OPENCLAW_DIR        - OpenClaw installation directory (auto-detected)
    QDRANT_BINARY       - Path to Qdrant binary
    QDRANT_PORT         - Qdrant port (default: 6333)
    CHECK_INTERVAL      - Monitor check interval in seconds (default: 60)

Auto-Discovery of OpenClaw:
The supervisor will search these locations for OpenClaw:
    - $OPENCLAW_DIR environment variable
    - ~/.openclaw (standard OpenClaw installation)
    - ~/.claude (Claude Code / OpenClaw fork)
    - ~/moltbot (Moltbot installation)
    - ~/clawd (Alternative OpenClaw location)

Usage:
    python supervisor.py --start        # Start all services
    python supervisor.py --status       # Show status
    python supervisor.py --monitor      # Auto-restart loop (run in background)
    python supervisor.py --stop         # Stop all services
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime
import requests

# ═══════════════════════════════════════════════════════════════
# OPENCLAW AUTO-DISCOVERY
# ═══════════════════════════════════════════════════════════════

def discover_openclaw():
    """Auto-discover OpenClaw installation directory."""
    
    # Priority order for discovery
    search_paths = [
        # Environment variable (highest priority)
        os.environ.get("OPENCLAW_DIR"),
        
        # Standard installations
        Path.home() / ".openclaw",
        Path.home() / ".claude",        # Claude Code / OpenClaw fork
        Path.home() / "moltbot",        # Moltbot
        Path.home() / "clawd",          # Alternative OpenClaw
    ]
    
    for path in search_paths:
        if path:
            # Handle Path objects and strings
            p = Path(path) if isinstance(path, (str, Path)) else None
            if p and p.exists() and (p / "agents").exists():
                return str(p.resolve())
    
    return None  # Not found

OPENCLAW_DIR = discover_openclaw()

# Load environment or use defaults
MEMORY_ROOT = Path(os.environ.get("MOLTING_MEMORY_DIR", Path.home() / ".molting-memory"))

CONFIG = {
    "openclaw": {
        "dir": OPENCLAW_DIR,
        "sessions": [
            # Auto-discovered paths if OpenClaw found
        ],
    },
    "qdrant": {
        "binary": os.environ.get("QDRANT_BINARY", "/home/vel/qdrant"),
        "port": int(os.environ.get("QDRANT_PORT", 6333)),
        "restart_delay": 5,
    },
    "check_interval": int(os.environ.get("CHECK_INTERVAL", 60)),
}

# Build session directories from discovered OpenClaw
if OPENCLAW_DIR:
    openclaw_path = Path(OPENCLAW_DIR)
    CONFIG["openclaw"]["sessions"] = [
        str(openclaw_path / "agents" / "main" / "sessions"),      # OpenClaw v3
        str(openclaw_path / "moltbot" / "agents" / "main" / "sessions"),  # Moltbot v2
        str(openclaw_path / ".clawdbot" / "agents" / "main" / "sessions"), # Clawdbot v1
    ]
else:
    CONFIG["openclaw"]["sessions"] = []

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
    
    # OpenClaw Discovery
    if OPENCLAW_DIR:
        print(f"OpenClaw:    ✅ Found at {OPENCLAW_DIR}")
    else:
        print("OpenClaw:    ⚠️  Not found (set OPENCLAW_DIR)")
    
    # Session directories
    sessions = CONFIG["openclaw"]["sessions"]
    if sessions:
        print(f"Sessions:    {len(sessions)} directories configured")
    else:
        print("Sessions:    Not configured")
    
    # Qdrant
    qdrant_ok = check_qdrant()
    qdrant_pid = get_pid("qdrant")
    
    print(f"\nQdrant:      {'✅ Running' if qdrant_ok else '❌ Down'}")
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
