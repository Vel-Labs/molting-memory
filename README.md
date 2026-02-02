# 🧠 Molting Memory v1.0

**Persistent, queryable memory for AI agents. $0 cost. Evolving continuously.**

---

## ✨ v1.0: The Magic Moment

When you run onboarding, your agent **discovers existing sessions** from ALL OpenClaw versions:

```
🔍 SESSION DISCOVERY
Searched 4 directories:
   ✅ .openclaw/agents/main/sessions (OpenClaw v3)
   ✅ moltbot/agents/main/sessions (Moltbot v2)
   ✅ .clawdbot/agents/main/sessions (Clawdbot v1)

Found 3 session files with 1,247 messages

💡 These sessions can be vectorized into your memory!

Vectorize these sessions into memory? [Y/n]: y

📚 Vectorizing sessions...
✅ Ingestion complete: 884 entries

🎉 Your agent now remembers 1,247 messages from across ALL versions!
```

**One system. All your history. Forever.**

---

## Quick Start (5 Minutes)

```bash
# 1. One-line install
curl -sSL https://raw.githubusercontent.com/Vel-Labs/molting-memory/main/install.sh | bash

# 2. Run onboarding (discovers sessions automatically!)
python scripts/onboard.py

# 3. Your agent has memory!
```

---

## What You Get

| Feature | Description |
|---------|-------------|
| 🔍 **Session Discovery** | Scans past conversations, offers to vectorize |
| 📝 **Human-Readable Memory** | Daily .md files you can read |
| 🔒 **Entity Quarantine** | New entities need validation |
| ⚔️ **Conflict Detection** | "Wait, you said venv AND conda?" |
| 💾 **Auto-Consolidation** | Weekly summaries prevent bloat |
| 🛡️ **Graceful Degradation** | Works even if Qdrant down |

### Quick Start (5 Minutes)

```bash
# 1. Run install script
curl -sSL https://raw.githubusercontent.com/Vel-Labs/molting-memory/main/install.sh | bash

# 2. Run onboarding
python scripts/onboard.py

# 3. Start using it!
# Just say "Remember this: ..." to your agent
```

### How Memory Works

```
TODAY'S MEMORY (2026-02-01.md)
├── 10:00 - DECISION: We use venv for Python
├── 14:30 - ACTION: Review weekly
└── 16:45 - IMPORTANT: Dr. Smith is project lead

WEEKLY SUMMARY (Week_2026-02-01.md)
├── Decisions: 5 extracted
├── Preferences: 3 identified  
└── Actions: 7 listed
```

### Reading Your Memory

Your memories are just text files:

```bash
# Today's memories (adjust path to your OpenClaw data directory)
cat ~/.openclaw/memory/2026-02-01.md

# Yesterday's memories
cat ~/.openclaw/memory/2026-01-31.md

# Weekly summaries
cat ~/.openclaw/memory/distilled/Week_2026-02-01.md
```

### Validating Entities

When your agent discovers a new person/project:

1. It goes to **quarantine** (safety first!)
2. You review it: `cat memory/entities/_quarantine/new_entity.md`
3. You validate it: `python scripts/memory_brain.py --validate "New Entity"`
4. It moves to your main entities folder

---

## For Agents

### Skill ID: `molting-memory`

### System Prompts

**On skill load**:
```
You have access to the molting-memory skill.
Memory location: ~/.openclaw/memory/
Qdrant URL: http://127.0.0.1:6333

Key behaviors:
1. Listen for memory triggers ("remember this", "don't forget")
2. Save important context to daily memory files
3. Discover and quarantine new entities
4. Query memory before responding to context-dependent questions
```

**Memory file format** (write to `~/.openclaw/memory/YYYY-MM-DD.md`):
```markdown
## HH:MM - CATEGORY [importance]

Your memory content here.

---
```

**Categories**: `DECISION`, `ACTION`, `IMPORTANT`, `GENERAL`
**Importance**: `normal`, `high`

### Command Interface

```bash
# Save memory
python scripts/memory_brain.py --save "content" --category decision

# Query memory
python scripts/memory_brain.py --query "search terms"

# Entity discovery & quarantine
python scripts/memory_brain.py --discover "conversation text"
python scripts/memory_brain.py --quarantine-list
python scripts/memory_brain.py --validate "entity name"

# Consolidation
python scripts/memory_brain.py --consolidate-weekly

# Status
python scripts/memory_brain.py --status
```

### Response Formats

**Save Response**:
```
✅ Saved to ~/.openclaw/memory/2026-02-01.md
Category: DECISION | Importance: normal
```

**Query Response**:
```
🔍 Results for: venv
==================================================

📅 Daily (2 files):
  - 2026-02-01: We prefer using venv for Python...
  - 2026-01-30: ...venv configuration notes...

📆 Weekly (1 summary):
  - Week_2026-02-01: Decision: venv for Python...

🔢 Vectors (3 matches):
  - mem_steven (0.92): Python environment preference...
```

**Quarantine List**:
```
🔒 Entities in Quarantine (2):
  - Dr. Smith (since 2026-02-01)
  - Project Alpha (since 2026-02-01)
```

### Memory Triggers

Detect these phrases and auto-save:

| Pattern | Auto-Category |
|---------|---------------|
| "Remember this:" | GENERAL |
| "Don't forget:" | IMPORTANT |
| "Make sure to:" | ACTION |
| "We decided:" | DECISION |
| "This is important:" | IMPORTANT |

### Entity Quarantine Protocol

1. **Discover**: Run `--discover "text"` on new conversation
2. **Quarantine**: Entities go to `entities/_quarantine/`
3. **Validate**: Run `--validate "entity_name"` to promote
4. **Use**: After validation, entity is queryable

### Boot Protocol

On every session start:

```python
# Check Qdrant
if not curl http://127.0.0.1:6333/collections:
    start_qdrant()

# Load recent context
recent_memory = query_memory("what were we working on recently")

# Check quarantine
quarantined = get_quarantine_list()
if quarantined:
    alert_human(f"New entities awaiting validation: {quarantined}")
```

---

## Directory Structure

```
memory-system/
├── README.md                    # This file
├── SKILL.md                     # Agent skill documentation
├── install.sh                   # One-line install
├── scripts/
│   ├── onboard.py              # Initial setup questionnaire
│   ├── vectorize.py            # Vector indexing
│   └── memory_brain.py         # Core logic (v2.0)
└── config/
    ├── config.json             # Template configuration
    └── user_config.json        # User preferences (generated)

memory/                          # YOUR MEMORY DATA
├── YYYY-MM-DD.md               # Daily memory (human-readable)
├── entities/
│   ├── _quarantine/            # Entities awaiting validation
│   │   └── new_entity.md
│   └── validated_entity.md
└── distilled/
    └── Week_YYYY-MM-DD.md      # Weekly summaries
```

---

## Configuration

### User Config (`config/user_config.json`)

```json
{
  "user": {
    "name": "Your Name",
    "preferences": {
      "communication_style": "direct",
      "work_schedule": "morning"
    }
  },
  "collections": {
    "mem_user": {
      "desc": "Your preferences",
      "keywords": ["user", "preferences"]
    }
  },
  "cron": {
    "light": "*/30 * * * *",
    "heavy": "0 */2 * * *"
  }
}
```

---

## Cron Jobs

Add to `crontab -e`:

```bash
# Weekly consolidation (Monday 9 AM)
0 9 * * 1 cd /path/to/memory-system && python scripts/memory_brain.py --consolidate-weekly

# Daily cleanup (midnight)
0 0 * * * cd /path/to/memory-system && python scripts/memory_brain.py --cleanup

### Session Pipeline (Optional)

Automatically ingest OpenClaw sessions:

```bash
# Ingest last hour of sessions (run every hour via cron)
python scripts/ingest_sessions.py --hours 1

# Ingest all sessions once
python scripts/ingest_sessions.py
```

Sessions are read from `~/.openclaw/agents/main/sessions/*.jsonl` and saved to daily memory files.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Qdrant not running | `qdrant --uri http://127.0.0.1:6333 &` |
| Memory not saving | Check `~/.openclaw/memory/` exists and is writable |
| Entities not quarantining | Run `--discover` explicitly |
| Can't find memory | Check `memory/YYYY-MM-DD.md` files |

---

## Resources

- **Full Docs**: https://github.com/Vel-Labs/molting-memory
- **Qdrant**: https://qdrant.tech/documentation/

---

## 🧪 Testing

### Local Test Script

```bash
cd memory-system
bash test_install.sh
```

Runs basic validation:
- Clean venv creation
- Qdrant startup
- Vectorize script
- Memory brain commands
- Session ingest
- Crontab generation

### Comprehensive Test

```bash
cd memory-system
bash test_comprehensive.sh
```

Full end-to-end validation:
- Creates realistic session data
- Runs full ingest pipeline
- Tests vectorization and queries
- Validates conflict detection
- Entity discovery and quarantine
- All documentation

### Docker Test

```bash
cd memory-system
docker build -f Dockerfile.e2e -t memory-e2e .
docker run -it --rm memory-e2e
```

Runs comprehensive test in isolated Docker container.

---

## 🗺️ Multi-Version Support

Works with sessions from ALL OpenClaw versions:

| Version | Path | Status |
|---------|------|--------|
| **Clawdbot** (v1) | `~/.clawdbot/agents/main/sessions/` | ✅ Auto-detected |
| **Moltbot** (v2) | `~/moltbot/agents/main/sessions/` | ✅ Auto-detected |
| **OpenClaw** (v3) | `~/.openclaw/agents/main/sessions/` | ✅ Auto-detected |

### How It Works

The ingest script checks all directories automatically (configurable via `config/user_config.json`):

```python
# Default session directories - adjust path to match YOUR setup
SESSION_DIRS = [
    Path("~/.openclaw/agents/main/sessions"),      # OpenClaw v3
    Path("~/moltbot/agents/main/sessions"),        # Moltbot v2
    Path("~/.clawdbot/agents/main/sessions"),      # Clawdbot v1
]
```

### Filter by Version

```bash
# Only clawdbot sessions
python scripts/ingest_sessions.py --clawdbot

# Only moltbot sessions
python scripts/ingest_sessions.py --moltbot

# Only openclaw sessions
python scripts/ingest_sessions.py --openclaw
```

### Import Legacy Data

Coming from Moltbot or Clawdbot? Run:

```bash
# Discover all sessions across all versions
python scripts/ingest_sessions.py

# Or filter to specific version
python scripts/ingest_sessions.py --moltbot
```

---

## 🪝 CLAW TO ACTION

**Try it, share it, if you like it ⭐ star the repo, provide feedback!**

Built with ❤️ by the Velcrafting Agent System
