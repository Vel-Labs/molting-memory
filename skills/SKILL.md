# Agentic Memory System Skill

**Skill ID**: `agentic-memory`
**Version**: 1.0.0
**Last Updated**: 2026-02-01
**Name**: Molting Memory
**Author**: Ren (Velcrafting Agent System)

---

## Overview

**Molting Memory** - Persistent, queryable memory for AI agents. Named for the continuous renewal of memory, like an organism shedding its outer layer to grow.

This skill gives your AI agent persistent memory that:
- Works across ALL OpenClaw versions (Clawdbot → Moltbot → OpenClaw)
- Uses human-readable daily files
- Implements entity quarantine (validation before promotion)
- Includes keyword triggers ("remember this", "don't forget")
- Costs $0 (self-hosted Qdrant)

### Multi-Version Support

```python
SESSION_DIRS = [
    "/home/vel/.openclaw/agents/main/sessions",      # OpenClaw v3
    "/home/vel/.openclaw/moltbot/agents/main/sessions", # Moltbot v2
    "/home/vel/.clawdbot/agents/main/sessions",       # Clawdbot v1
]
```

## Quick Start

### One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/velcrafting/agentic-memory/main/install.sh | bash
```

### Onboarding (v1.0 Flow)

```bash
python scripts/onboard.py
```

**Onboarding now does:**

1. 🔍 **Discovers sessions** - Scans OpenClaw sessions, reports message count
2. 💡 **Offers vectorization** - "Vectorize these sessions into memory?"
3. 📋 **Personalization** - Name, projects, work schedule
4. 📊 **Retention settings** - Daily file retention, vector retention
5. 🔧 **Cron setup** - Automatic consolidation schedule

---

## v1.0: Session Discovery Flow

When you run onboarding for the first time:

```
🔍 SESSION DISCOVERY
Found 3 session files with 1,247 messages

💡 These sessions can be vectorized into your memory!

Vectorize these sessions into memory? [Y/n]: y

📚 Vectorizing sessions...
✅ Ingestion complete: 884 entries
🎉 SESSION VECTORIZATION COMPLETE!
```

This is the **key value add** - your agent immediately has context from past conversations.

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────┐
│              MEMORY TIERS                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  IMMEDIATE                                           │
│  ├── In-memory during conversation                  │
│  └── Session transcript saved                       │
│                                                     │
│  DAILY (Short-Term)                                 │
│  ├── Human-readable .md files (2026-02-01.md)       │
│  ├── Categories: decision, action, general          │
│  └── Auto-consolidated after 7 days                 │
│                                                     │
│  WEEKLY (Medium-Term)                               │
│  ├── Distilled summaries (Week_2026-02-01.md)       │
│  ├── Key decisions, preferences, actions            │
│  └── Auto-created every Monday                      │
│                                                     │
│  LONG-TERM                                          │
│  ├── Monthly distilled summaries                    │
│  └── Queryable for historical context               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Human-Readable Daily Memory

**Location**: `/home/vel/.openclaw/memory/YYYY-MM-DD.md`

**Format**:
```markdown
## 17:08 - DECISION [high]

We prefer using venv for Python projects

---

## 14:30 - ACTION [normal]

Remember to run weekly consolidation every Monday

---

## 10:15 - GENERAL [normal]

Discussed project timeline with Dr. Smith

---
```

**Benefits**:
- Humans can read it directly
- No special tools needed
- Git-diff friendly
- Easy to edit manually

---

## Entity Quarantine

**Purpose**: Prevent memory bloat from false-positive entity detection.

### The Flow

```
1. DISCOVERY    → Entity detected in conversation
2. QUARANTINE   → Placed in entities/_quarantine/
3. VALIDATION   → Human or agent confirms entity
4. PROMOTION    → Moved to entities/ collection
```

### Commands

```bash
# Discover and auto-quarantine entities
python scripts/memory_brain.py --discover "I met with Dr. Smith about Project Alpha"

# List quarantined entities
python scripts/memory_brain.py --quarantine-list

# Validate and promote
python scripts/memory_brain.py --validate "Dr. Smith"

# Validate with target collection
python scripts/memory_brain.py --validate "Dr. Smith" --collection mem_clients
```

### Quarantine File Format

```markdown
# Dr. Smith (IN QUARANTINE)

*Discovered: 2026-02-01 17:09*
*Status: PENDING VALIDATION*

## Context

I met with Dr. Smith about the quarterly review.

## Keywords

- Dr. Smith
- dr_smith

## Validation Checklist

- [ ] Confirm entity exists
- [ ] Determine entity type (person/project/topic)
- [ ] Assign to appropriate collection

---

*Auto-generated by MemoryBrain.*
```

### Validated Entity Format

```markdown
# Dr. Smith (VALIDATED)

*Discovered: 2026-02-01 17:09*
*Validated: 2026-02-01 17:15*

## Context

I met with Dr. Smith about the quarterly review.

## Validation Details

- Target Collection: mem_steven
- Keywords: dr_smith, Dr. Smith
- Confirmed by: human

---
```

---

## Weekly Consolidation

**Purpose**: Prevent daily file bloat while preserving context.

### How It Works

Every Monday, daily files from the previous week are consolidated into a single weekly summary.

### Weekly Summary Format

```markdown
# Weekly Memory Summary - 2026-01-27 to 2026-02-02

*Generated: 2026-02-03 09:00*

## Consolidated from 7 daily entries

## Decisions

- We prefer using venv for Python projects
- Weekly consolidation happens every Monday
- Dr. Smith confirmed as project advisor

## Preferences

- Direct communication style
- Morning work sessions preferred

## Action Items

- Run memory consolidation weekly
- Validate quarantined entities

---

*See daily files (2026-01-27.md through 2026-02-02.md) for full detail.*
```

### Commands

```bash
# Manually trigger weekly consolidation
python scripts/memory_brain.py --consolidate-weekly

# Query weekly memory
python scripts/memory_brain.py --query "venv" --include-weekly true
```

---

## Keyword Triggers

**Agents with this skill SHOULD listen for memory trigger phrases.**

### Trigger Keywords

| Phrase | Category | Importance |
|--------|----------|------------|
| "Remember this:" | general | normal |
| "Don't forget:" | important | high |
| "Make sure to:" | action | normal |
| "We decided:" | decision | normal |
| "This is important:" | important | high |
| "For future reference:" | long-term | normal |

### Example

**User**: "Remember this: we always use venv for Python projects"

**Agent Response**:
1. Detects "remember this" trigger
2. Saves to daily memory with DECISION category
3. Responds: "✅ Got it. Saved to 2026-02-01.md"

---

## Commands Reference

### Memory Management

| Command | Description |
|---------|-------------|
| `--save "text"` | Save to daily memory |
| `--category decision/action/important` | Set category |
| `--query "text"` | Search all memory tiers |
| `--status` | Show memory status |

### Entity Management

| Command | Description |
|---------|-------------|
| `--discover "text"` | Discover & quarantine entities |
| `--quarantine-list` | List entities in quarantine |
| `--validate "name"` | Validate entity from quarantine |

### Consolidation

| Command | Description |
|---------|-------------|
| `--consolidate-weekly` | Consolidate daily → weekly |

### Query Options

```bash
# Query all tiers
python scripts/memory_brain.py --query "venv"

# Query specific tiers
python scripts/memory_brain.py --query "venv" --include-daily true --include-weekly true --include-vectors true
```

---

## Directory Structure

```
memory/
├── YYYY-MM-DD.md              # Daily memory (human-readable)
├── entities/
│   ├── _quarantine/           # Entities awaiting validation
│   │   └── entity_name.md
│   └── entity_name.md         # Validated entities
└── distilled/
    └── Week_YYYY-MM-DD.md     # Weekly summaries
```

---

## AGENT INSTRUCTION: SOUL.md Boot Protocol

**Every agent with this skill SHOULD implement the SOUL.md boot protocol.**

### Why?

1. **Memory consistency**: Agent always has context on startup
2. **Human-readable**: Daily files can be read directly
3. **Quarantine safety**: New entities require validation
4. **No bloat**: Weekly consolidation prevents sprawl

### How to Implement

Add to SOUL.md:

```markdown
## Memory System

**Location**: /home/vel/.openclaw/memory/

**On Boot**:
1. Check Qdrant running: `curl http://127.0.0.1:6333/collections`
2. If not running: Start Qdrant
3. Check for daily memory file (today's date)
4. Query recent memory: `--query "what were we working on"`

**Memory Format**:
- Daily files: YYYY-MM-DD.md (human-readable)
- Weekly files: Week_YYYY-MM-DD.md (distilled)

**Quarantine Rule**:
- Any discovered entity starts in _quarantine/
- Must be validated before use: `--validate "entity_name"`
```

---

## Cron Setup (Auto-Consolidation)

```bash
# Add to crontab (crontab -e)

# Save to memory on user trigger (handled by agent)

# Weekly consolidation - Every Monday at 9 AM
0 9 * * 1 cd /path/to/memory-system && python scripts/memory_brain.py --consolidate-weekly

# Monthly consolidation - 1st of month at 2 AM
0 2 1 * * cd /path/to/memory-system && python scripts/memory_brain.py --consolidate-monthly

# Session ingestion - Every hour
0 * * * * cd /path/to/memory-system && python scripts/ingest_sessions.py --hours 1
```

---

## Session Pipeline (Optional)

**Automatically ingest OpenClaw session transcripts into memory.**

### How It Works

1. OpenClaw sessions saved to: `/home/vel/.openclaw/agents/main/sessions/*.jsonl`
2. Ingestion script parses JSONL format
3. Extracts user/assistant messages
4. Saves to daily memory files

### Usage

```bash
# Ingest last 24 hours of sessions
python scripts/ingest_sessions.py --hours 24

# Ingest all sessions
python scripts/ingest_sessions.py

# Dry run (don't save)
python scripts/ingest_sessions.py --dry-run
```

### Cron Setup (Optional)

```bash
# Ingest sessions every hour
0 * * * * cd /path/to/memory-system && python scripts/ingest_sessions.py --hours 1
```

### What Gets Ingested

- User messages (if substantive, >50 chars)
- Assistant responses (full context)
- Skips: HEARTBEAT checks, very short messages

### Example Output

```
📄 Processing: abc123.jsonl
   Found 658 messages
   Extracted 589 memory entries
   Saved 589 entries to daily memory

✅ Ingestion complete: 884 entries
```

---

## Troubleshooting

### No daily memory file created?

```bash
# Check memory directory exists
ls -la /home/vel/.openclaw/memory/

# Check permissions
touch /home/vel/.openclaw/memory/test.md
```

### Entities not quarantined?

```bash
# Run discovery with verbose
python scripts/memory_brain.py --discover "I met with Dr. Smith"

# Check quarantine list
python scripts/memory_brain.py --quarantine-list
```

### Weekly consolidation failed?

```bash
# Check daily files exist
ls /home/vel/.openclaw/memory/*.md

# Run manually
python scripts/memory_brain.py --consolidate-weekly
```

---

## Files

```
memory-system/
├── README.md              # Human-readable quick start
├── SKILL.md               # This file (for agents)
├── install.sh             # One-line install script
├── scripts/
│   ├── onboard.py         # Initial configuration
│   ├── vectorize.py       # Vector indexing
│   └── memory_brain.py    # Core memory logic (v2.0)
└── config/
    └── user_config.json   # User preferences
```

---

## Resources

- **Concept Guide**: [Agentic Memory: A Practical Guide](https://docs.google.com/document/d/1eQDmLjwr3oLQgKRLDSHwmw13YaLjCR0V-FAIB07pzn8/edit)
- **Implementation Guide**: [Velcrafting Agentic Memory System](https://docs.google.com/document/d/1MOcD1N5c5eXkfo3dBY3GduM-2F8B8eTvx-3ZvUgBw5E/edit)
- **Qdrant Docs**: https://qdrant.tech/documentation/

---

## CLAW TO ACTION 🪝

**Try it, share it, if you like it ⭐ star the repo, provide feedback!**

---

*Skill Version: 2.0.0 | Compatible with OpenClaw*
