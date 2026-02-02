#!/usr/bin/env python3
"""
Memory System Onboarding Questionnaire (v1.0)

Run this to configure your Molting Memory system.
Answers are saved to memory/entities/your_preferences.md

Two Modes:
- "Just Do It" - Uses sensible defaults, fast setup
- "Help Me Configure" - Interactive, full customization
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# SESSION DISCOVERY - Auto-detect all OpenClaw versions
# ═══════════════════════════════════════════════════════════════

# Default session directories (relative paths)
DEFAULT_SESSION_DIRS = [
    "~/.openclaw/agents/main/sessions",      # OpenClaw v3
    "~/moltbot/agents/main/sessions",        # Moltbot v2
    "~/.clawdbot/agents/main/sessions",      # Clawdbot (original)
    "~/.clawd/agents/main/sessions",         # Alternative v3 path
]

def find_sessions():
    """Find all session files across all possible directories."""
    all_files = []
    found_dirs = []

    for sess_dir_str in DEFAULT_SESSION_DIRS:
        sess_dir = Path(os.path.expanduser(sess_dir_str))
        if sess_dir.exists():
            files = list(sess_dir.glob("*.jsonl"))
            if files:
                found_dirs.append(str(sess_dir))
                all_files.extend(files)

    return all_files, found_dirs

def count_messages(session_files):
    """Count messages in session files."""
    total_messages = 0
    for sf in session_files:
        try:
            with open(sf, 'r') as f:
                for line in f:
                    if '"type":"message"' in line:
                        total_messages += 1
        except:
            pass
    return total_messages

print("=" * 60)
print("🧠 MOLTING MEMORY v1.0")
print("=" * 60)
print()

# Session Discovery First!
session_files, found_dirs = find_sessions()
session_count = len(session_files)
message_count = count_messages(session_files)

print("🔍 SESSION DISCOVERY")
print("-" * 40)

if found_dirs:
    print(f"Searched {len(found_dirs)} directories:")
    for d in found_dirs:
        print(f"   ✅ {d}")
    print()
    print(f"Found {session_count} session files with {message_count} messages")
else:
    print("No session directories found (this is fine for new installs)")
    print()
    print("💡 After your agent runs for a while, sessions will appear here.")

print()

if message_count > 0:
    print("💡 These sessions can be vectorized into your memory!")
    print()

    ingest_choice = input("Vectorize these sessions into memory? [Y/n]: ").strip().lower()
    if ingest_choice in ["", "y", "yes"]:
        print()
        print("📚 Vectorizing sessions...")
        import subprocess
        ingest_script = Path(__file__).parent / "ingest_sessions.py"
        result = subprocess.run(
            [sys.executable, str(ingest_script)],
            capture_output=True, text=True
        )
        print(result.stdout)

        # Extract entity discoveries from output
        if "Discovered entities" in result.stdout:
            print()
            print("🎉 SESSION VECTORIZATION COMPLETE!")
    else:
        print("Skipped session vectorization (can run later: python scripts/ingest_sessions.py)")
else:
    print("No messages found yet (sessions need to accumulate first)")

print()
print("📋 SETUP MODE")
print("-" * 40)
print()
print("  🚀 JUST DO IT")
print("     • Uses sensible defaults")
print("     • Fast setup (~2 min)")
print("     • Auto-configures SOUL.md boot protocol")
print()
print("  🔧 HELP ME CONFIGURE")
print("     • Interactive customization")
print("     • Choose your own schedule")
print("     • Decide on SOUL.md integration")
print()

mode = input("Choose mode [1=Just Do It, 2=Help Me Configure]: ").strip()

if mode == "1":
    mode = "fast"
    print("\n🚀 Running in JUST DO IT mode...\n")
elif mode == "2":
    mode = "configure"
    print("\n🔧 Running in HELP ME CONFIGURE mode...\n")
else:
    mode = "fast"
    print("\n🚀 Defaulting to JUST DO IT mode...\n")

# ═══════════════════════════════════════════════════════════════
# QUESTIONS
# ═══════════════════════════════════════════════════════════════

answers = {}

if mode == "fast":
    print("📋 PERSONALIZATION")
    print("-" * 40)
    answers["name"] = input("Your name: ").strip() or "User"
    answers["communication_style"] = "direct"
    answers["work_schedule"] = "morning"
    answers["projects"] = input("Current projects (comma-separated): ").strip() or "general"
    answers["entities"] = answers["name"]
    
    # Auto-add SOUL.md boot protocol
    answers["add_soul_boot_protocol"] = "yes"
    print()
    print(f"✅ SOUL.md boot protocol enabled")
    print()
    
    # Adaptive cron
    if answers["work_schedule"] == "morning":
        answers["cron_light"] = "*/30 * * * *"
        answers["cron_heavy"] = "0 */2 * * *"
    elif answers["work_schedule"] == "evening":
        answers["cron_light"] = "*/30 * * * *"
        answers["cron_heavy"] = "0 */4 * * *"
    else:
        answers["cron_light"] = "*/30 * * * *"
        answers["cron_heavy"] = "0 */2 * * *"
    
    print(f"📅 Cron: light every 30min, heavy every 2 hours")
    print()

else:
    print("📋 PERSONALIZATION")
    print("-" * 40)
    answers["name"] = input("Your name: ").strip() or "User"
    print()
    
    print("💬 COMMUNICATION")
    print("-" * 40)
    answers["communication_style"] = input("Style (direct, collaborative, detailed): ").strip() or "direct"
    answers["tone_preference"] = input("Tone (casual, formal, playful): ").strip() or "casual"
    print()
    
    print("💻 TECHNICAL")
    print("-" * 40)
    answers["python_env"] = input("Python environment (venv, conda, none): ").strip() or "venv"
    print()
    
    print("📅 WORK PATTERNS")
    print("-" * 40)
    answers["work_schedule"] = input("Best time (morning, afternoon, evening, night): ").strip() or "morning"
    answers["session_length"] = input("Session length (short, medium, long): ").strip() or "medium"
    print()
    
    print("🎯 PROJECTS")
    print("-" * 40)
    answers["projects"] = input("Current projects (comma-separated): ").strip() or "general"
    answers["entities"] = answers["name"]
    print()
    
    print("🤖 SOUL.MD INTEGRATION")
    print("-" * 40)
    print("Add boot protocol for automatic memory wake-up?")
    soul_choice = input("[y/n]: ").strip().lower()
    answers["add_soul_boot_protocol"] = "yes" if soul_choice in ["y", "yes"] else "no"
    print()
    
    print("📅 CRON SCHEDULE")
    print("-" * 40)
    if answers["work_schedule"] == "morning":
        default_light = "*/30 * * * *"
        default_heavy = "0 */2 * * *"
    elif answers["work_schedule"] == "evening":
        default_light = "*/30 * * * *"
        default_heavy = "0 */4 * * *"
    else:
        default_light = "*/30 * * * *"
        default_heavy = "0 */2 * * *"
    
    light_input = input(f"Light consolidation [{default_light}]: ").strip()
    answers["cron_light"] = light_input or default_light
    
    heavy_input = input(f"Heavy consolidation [{default_heavy}]: ").strip()
    answers["cron_heavy"] = heavy_input or default_heavy
    print()

# ═══════════════════════════════════════════════════════
# MEMORY RETENTION (v1.0 Feature)
# ═══════════════════════════════════════════════════════

print("📊 MEMORY RETENTION")
print("-" * 40)
print("Daily files are purged after vectorization (vectors remain).")
print()

retention = input("Daily file retention (days) [7]: ").strip()
retention = int(retention) if retention.isdigit() else 7
print(f"  ✓ Daily files: {retention} days")

print()
short_term = input("Short-term vector retention (days) [30]: ").strip()
short_term = int(short_term) if short_term.isdigit() else 30
print(f"  ✓ Short-term vectors: {short_term} days")

auto_prune = input("Enable auto-pruning? [Y/n]: ").strip().lower()
auto_prune_enabled = auto_prune in ["", "y", "yes"]
print()

# ═══════════════════════════════════════════════════════
# SAVE CONFIG
# ═══════════════════════════════════════════════════════

memory_dir = Path("/home/vel/.openclaw/memory/entities")
memory_dir.mkdir(parents=True, exist_ok=True)

output_file = memory_dir / "your_preferences.md"

content = f"""# User Preferences - v1.0

*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*

## Basic Info

- **Name**: {answers.get('name', 'User')}
- **Mode**: {mode}

## Communication

- **Style**: {answers.get('communication_style', 'Not specified')}
- **Tone**: {answers.get('tone_preference', 'Not specified')}

## Technical

- **Python Environment**: {answers.get('python_env', 'Not specified')}

## Work Patterns

- **Schedule**: {answers.get('work_schedule', 'Not specified')}
- **Session**: {answers.get('session_length', 'Not specified')}

## Projects

- **Current**: {answers.get('projects', 'Not specified')}

## Retention

- **Daily Files**: {retention} days
- **Short-Term Vectors**: {short_term} days
- **Auto-Prune**: {'Enabled' if auto_prune_enabled else 'Disabled'}

## Cron

- **Light**: {answers.get('cron_light', 'Not specified')}
- **Heavy**: {answers.get('cron_heavy', 'Not specified')}

## SOUL.md Boot

- **Enabled**: {answers.get('add_soul_boot_protocol', 'Not specified')}

---

*Memory System v1.0*
"""

output_file.write_text(content)

# Generate user_config.json
config_file = Path("/home/vel/.openclaw/memory-system/config/user_config.json")

entities = [e.strip() for e in answers.get('entities', '').split(',') if e.strip()]
collections = {}
for entity in entities:
    safe_name = entity.lower().replace(" ", "_")
    collections[f"mem_{safe_name}"] = {
        "desc": f"{entity} context",
        "keywords": [entity.lower(), safe_name]
    }
collections["mem_sessions"] = {"desc": "Session transcripts", "keywords": ["session", "transcript"]}
collections["mem_distilled"] = {"desc": "Weekly summaries", "keywords": ["weekly", "summary"]}

config = {
    "user": {"name": answers.get("name", "User")},
    "collections": collections,
    "qdrant": {"url": "http://127.0.0.1:6333"},
    "memory": {"dir": "/home/vel/.openclaw/memory"},
    "pruning": {
        "daily_file_retention_days": retention,
        "short_term_vector_days": short_term,
        "auto_prune_enabled": auto_prune_enabled
    },
    "cron": {
        "light": answers.get("cron_light", "*/30 * * * *"),
        "heavy": answers.get("cron_heavy", "0 */2 * * *")
    },
    "soul_md": {"boot_protocol": answers.get("add_soul_boot_protocol", "no") == "yes"}
}

config_file.write_text(json.dumps(config, indent=2))

# ═══════════════════════════════════════════════════════
# GENERATE CRON
# ═══════════════════════════════════════════════════════

cron_file = Path("/home/vel/.openclaw/memory-system/crontab.txt")
cron_content = f"""# Agentic Memory System v1.0 - Cron Jobs
# Generated: {datetime.now().strftime("%Y-%m-%d")}

# Light consolidation
{answers.get('cron_light', '*/30 * * * *')} cd /home/vel/.openclaw/memory-system && python scripts/memory_brain.py --consolidate light

# Heavy consolidation
{answers.get('cron_heavy', '0 */2 * * *')} cd /home/vel/.openclaw/memory-system && python scripts/memory_brain.py --consolidate heavy

# Session ingestion (hourly)
0 * * * * cd /home/vel/.openclaw/memory-system && python scripts/ingest_sessions.py --hours 1

# Full re-index (daily at 2 AM)
0 2 * * * cd /home/vel/.openclaw/memory-system && python scripts/vectorize.py --index-all
"""
cron_file.write_text(cron_content)

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════

print("=" * 60)
print("✅ MEMORY SYSTEM v1.0 SETUP COMPLETE!")
print("=" * 60)
print()
print(f"📄 Preferences: {output_file}")
print(f"⚙️  Config: {config_file}")
print(f"📅 Cron: {cron_file}")
print()
print("NEXT STEPS:")
print("  1. crontab {cron_file}")
print("  2. python scripts/vectorize.py --index-all")
print("  3. python scripts/vectorize.py --status")
print()
print("🧠 Your agent now has persistent memory!")
print("=" * 60)
