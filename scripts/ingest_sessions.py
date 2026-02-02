#!/usr/bin/env python3
"""
Session to Memory Ingestion Pipeline v1.0

Ingests session transcripts from ALL OpenClaw versions into memory:
- clawdbot (original)
- moltbot (v2)
- openclaw (v3)

Usage:
    python scripts/ingest_sessions.py           # Ingest all sessions
    python scripts/ingest_sessions.py --hours 4  # Ingest last 4 hours
    python scripts/ingest_sessions.py --clawdbot  # Only clawdbot sessions
    python scripts/ingest_sessions.py --moltbot  # Only moltbot sessions  
    python scripts/ingest_sessions.py --openclaw  # Only openclaw sessions
"""

import json
import glob
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser

# ═══════════════════════════════════════════════════════════════
# SESSION DIRECTORIES (All OpenClaw Versions)
# ═══════════════════════════════════════════════════════════════

# All possible session directories across versions
SESSION_DIRS = [
    Path("/home/vel/.openclaw/agents/main/sessions"),      # OpenClaw v3
    Path("/home/vel/.openclaw/moltbot/agents/main/sessions"), # Moltbot v2
    Path("/home/vel/.clawdbot/agents/main/sessions"),       # Clawdbot (original)
    Path("/home/vel/clawd/agents/main/sessions"),         # Alternative v3 path
]

MEMORY_DIR = Path("/home/vel/.openclaw/memory")

def find_all_session_files():
    """Find all session files across all OpenClaw versions."""
    all_files = []
    found_dirs = []
    
    for sess_dir in SESSION_DIRS:
        if sess_dir.exists():
            files = list(sess_dir.glob("*.jsonl"))
            if files:
                found_dirs.append(str(sess_dir))
                all_files.extend(files)
    
    return all_files, found_dirs

def parse_session_file(session_file):
    """Parse a JSONL session file and extract messages."""
    messages = []
    
    with open(session_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                entry = json.loads(line)
                
                # Handle both new (type=message) and old formats
                msg = entry.get("message") or entry.get("data", {})
                role = msg.get("role", "")
                
                # Extract content
                content_parts = msg.get("content", [])
                if isinstance(content_parts, str):
                    text_content = content_parts
                else:
                    text_content = ""
                    for part in content_parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_content += part.get("text", "")
                        elif isinstance(part, str):
                            text_content += part
                
                # Get timestamp
                timestamp = entry.get("timestamp") or entry.get("createdAt") or entry.get("date")
                if not timestamp:
                    # Try to get from file mtime
                    timestamp = datetime.fromtimestamp(
                        session_file.stat().st_mtime, tz=timezone.utc
                    ).isoformat()
                
                try:
                    if isinstance(timestamp, str):
                        dt = date_parser.parse(timestamp)
                    else:
                        dt = datetime.now(timezone.utc)
                except:
                    dt = datetime.now(timezone.utc)
                
                if text_content and role in ["user", "assistant"]:
                    messages.append({
                        "role": role,
                        "content": text_content,
                        "timestamp": dt
                    })
                    
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    
    return messages

def extract_memory_entries(messages):
    """Extract memory-worthy content from messages."""
    entries = []
    
    for msg in messages:
        content = msg["content"]
        role = msg["role"]
        
        # Skip heartbeat/system messages
        if any(x in content for x in ["HEARTBEAT_OK", "Read HEARTBEAT.md", "system:", "{"]):
            continue
        
        # Skip very short messages
        if len(content) < 50:
            continue
        
        entries.append({
            "content": content,
            "category": "conversation",
            "role": role
        })
    
    return entries

def save_to_daily_memory(entries, session_date=None):
    """Save entries to daily memory file."""
    if not entries:
        return 0
    
    if session_date is None:
        session_date = entries[0]["timestamp"]
    
    today = session_date.strftime("%Y-%m-%d")
    daily_file = MEMORY_DIR / f"{today}.md"
    
    with open(daily_file, 'a') as f:
        f.write(f"\n## {session_date.strftime('%H:%M')} - SESSION INGEST\n")
        f.write(f"*Ingested from {len(entries)} messages*\n\n")
        
        for entry in entries[:20]:
            preview = entry["content"][:500]
            if len(entry["content"]) > 500:
                preview += "..."
            f.write(f"**{entry['role'].upper()}**: {preview}\n\n")
        
        f.write("---\n")
    
    return len(entries)

def ingest_sessions(since_hours=None, source_filter=None):
    """Main ingestion function."""
    print(f"🧠 Session Ingestion Pipeline v1.0")
    print("=" * 50)
    
    # Find all session files
    session_files, found_dirs = find_all_session_files()
    
    if not session_files:
        print("⚠️  No session files found in any directory:")
        for d in SESSION_DIRS:
            print(f"   - {d}")
        return 0
    
    print(f"📂 Searched directories:")
    for d in found_dirs:
        print(f"   ✅ {d}")
    
    if source_filter:
        session_files = [f for f in session_files if source_filter in str(f)]
        print(f"\n🔍 Filtered to {len(session_files)} files")
    
    if not session_files:
        print("No files match filter")
        return 0
    
    if since_hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        print(f"\nIngesting sessions since {cutoff.strftime('%Y-%m-%d %H:%M')} UTC")
    else:
        cutoff = None
        print("\nIngesting all sessions")
    
    # Sort by modification time
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    total_entries = 0
    total_messages = 0
    
    for session_file in session_files:
        # Check cutoff
        if cutoff:
            mtime = datetime.fromtimestamp(
                session_file.stat().st_mtime, tz=timezone.utc
            )
            if mtime < cutoff:
                continue
        
        print(f"\n📄 {session_file.name}")
        
        messages = parse_session_file(session_file)
        print(f"   {len(messages)} messages")
        total_messages += len(messages)
        
        entries = extract_memory_entries(messages)
        print(f"   {len(entries)} memory entries")
        
        if entries:
            saved = save_to_daily_memory(entries, messages[0]["timestamp"])
            total_entries += saved
            print(f"   ✅ Saved {saved} entries")
    
    print(f"\n✅ Ingestion complete: {total_entries} entries from {total_messages} messages")
    return total_entries

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest OpenClaw sessions into memory"
    )
    parser.add_argument(
        "--hours", type=int, default=None,
        help="Ingest sessions from last N hours"
    )
    parser.add_argument(
        "--clawdbot", action="store_true",
        help="Only clawdbot sessions"
    )
    parser.add_argument(
        "--moltbot", action="store_true",  
        help="Only moltbot sessions"
    )
    parser.add_argument(
        "--openclaw", action="store_true",
        help="Only openclaw sessions"
    )
    
    args = parser.parse_args()
    
    # Determine filter
    source_filter = None
    if args.clawdbot:
        source_filter = "clawdbot"
    elif args.moltbot:
        source_filter = "moltbot"
    elif args.openclaw:
        source_filter = "openclaw"
    
    ingest_sessions(since_hours=args.hours, source_filter=source_filter)

if __name__ == "__main__":
    main()
