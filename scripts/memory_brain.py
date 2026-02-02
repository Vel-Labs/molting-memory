#!/usr/bin/env python3
"""
Memory Brain - Human-Readable Versioning with Entity Quarantine

Features:
- Daily memory files (human-readable: "2026-02-01.md")
- Weekly consolidation (prevents bloat)
- Entity quarantine (validation before promotion)
- Tiered memory (working → daily → weekly → monthly)
"""

import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

QDRANT_URL = "http://127.0.0.1:6333"
MEMORY_DIR = Path("/home/vel/.openclaw/memory")
QUARANTINE_DIR = MEMORY_DIR / "entities" / "_quarantine"
DISTILLED_DIR = MEMORY_DIR / "distilled"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Ensure directories exist
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
DISTILLED_DIR.mkdir(parents=True, exist_ok=True)

COLLECTIONS = {
    "mem_steven": "Preferences, history, context",
    "mem_kaylie": "Wedding, preferences",
    "mem_projects": "Active projects, decisions",
    "mem_velcrafting": "Business context",
    "mem_ren_collective": "Agent capabilities, decisions",
    "mem_sessions": "Session transcripts",
    "mem_distilled": "Weekly summaries",
}

# Memory trigger patterns
MEMORY_TRIGGERS = [
    (r"remember this[:\s]+(.+)", "normal"),
    (r"don't forget[:\s]+(.+)", "high"),
    (r"make sure to[:\s]+(.+)", "action"),
    (r"we decided[:\s]+(.+)", "decision"),
    (r"this is important[:\s]+(.+)", "high"),
    (r"for future reference[:\s]+(.+)", "long-term"),
]

class MemoryBrain:
    def __init__(self, timeout=5.0):
        self.client = QdrantClient(url=QDRANT_URL, timeout=timeout)
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.tracking_dir = MEMORY_DIR / ".memory_brain"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        self.load_tracking()
        self.init_collections()
    
    def load_tracking(self):
        f = self.tracking_dir / "access_tracking.json"
        if f.exists():
            with open(f, 'r') as fh:
                self.tracking = json.load(fh)
        else:
            self.tracking = {
                "access_logs": [],
                "memory_metrics": {},
                "last_consolidation": None,
                "daily_files": {},
                "weekly_summaries": {},
                "quarantine": [],
                "validated_entities": []
            }
        
        # Ensure structure
        for key in ["daily_files", "weekly_summaries", "quarantine", "validated_entities"]:
            if key not in self.tracking:
                self.tracking[key] = []
    
    def save_tracking(self):
        f = self.tracking_dir / "access_tracking.json"
        with open(f, 'w') as fh:
            json.dump(self.tracking, fh, indent=2)
    
    def init_collections(self):
        for coll in COLLECTIONS:
            try:
                self.client.create_collection(
                    collection_name=coll,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
            except:
                pass
    
    def _embed(self, text):
        return self.model.encode([text])[0].tolist()
    
    # ═══════════════════════════════════════════════════════════════
    # HUMAN-READABLE DAILY MEMORY
    # ═══════════════════════════════════════════════════════════════
    
    def save_daily_memory(self, content, importance="normal", category="general"):
        """Save memory to daily file with human-readable format."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = MEMORY_DIR / f"{today}.md"
        
        entry = f"""
## {datetime.now().strftime("%H:%M")} - {category.upper()} [{importance}]

{content}

---
"""
        
        # Append to daily file
        with open(daily_file, 'a') as f:
            f.write(entry)
        
        # Track this daily file
        if today not in self.tracking["daily_files"]:
            self.tracking["daily_files"][today] = []
        self.tracking["daily_files"][today].append({
            "content": content[:100],
            "category": category,
            "importance": importance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.save_tracking()
        
        return {
            "file": str(daily_file),
            "date": today,
            "category": category,
            "importance": importance
        }
    
    def query_daily_memory(self, query, days=7):
        """Query daily memory files from last N days."""
        results = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for file_path in MEMORY_DIR.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if file_date >= cutoff:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Simple keyword match for daily files
                        if query.lower() in content.lower():
                            results.append({
                                "file": str(file_path),
                                "date": file_path.stem,
                                "content_snippet": content[:500]
                            })
            except:
                continue
        
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # WEEKLY CONSOLIDATION (PREVENTS BLOAT)
    # ═══════════════════════════════════════════════════════════════
    
    def consolidate_to_weekly(self, week_start=None):
        """Consolidate daily files into weekly summary."""
        if week_start is None:
            # Get start of current week (Monday)
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
        
        week_start_str = week_start.strftime("%Y-%m-%d")
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start_str}_to_{week_end.strftime('%Y-%m-%d')}"
        
        weekly_file = DISTILLED_DIR / f"Week_{week_start_str}.md"
        
        # Collect all daily files from this week
        week_entries = []
        current = week_start
        while current <= week_end:
            date_str = current.strftime("%Y-%m-%d")
            daily_file = MEMORY_DIR / f"{date_str}.md"
            if daily_file.exists():
                with open(daily_file, 'r') as f:
                    week_entries.append(f.read())
            current += timedelta(days=1)
        
        if not week_entries:
            return None
        
        # Consolidate into weekly summary
        content = f"# Weekly Memory Summary - {week_start_str} to {week_end.strftime('%Y-%m-%d')}\n\n"
        content += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        content += f"## Consolidated from {len(week_entries)} daily entries\n\n"
        
        # Extract key decisions and preferences
        decisions = []
        preferences = []
        actions = []
        
        for entry_text in week_entries:
            if "[decision]" in entry_text.lower() or "decided" in entry_text.lower():
                decisions.append(entry_text)
            elif "prefer" in entry_text.lower() or "like" in entry_text.lower():
                preferences.append(entry_text)
            elif "[action]" in entry_text.lower() or "make sure" in entry_text.lower():
                actions.append(entry_text)
        
        if decisions:
            content += "## Decisions\n"
            for d in decisions[:5]:  # Top 5
                content += f"- {d.strip()}\n"
            content += "\n"
        
        if preferences:
            content += "## Preferences\n"
            for p in preferences[:5]:
                content += f"- {p.strip()}\n"
            content += "\n"
        
        if actions:
            content += "## Action Items\n"
            for a in actions[:5]:
                content += f"- {a.strip()}\n"
            content += "\n"
        
        content += "---\n*This is a weekly distilled summary. See daily files for full detail.*\n"
        
        # Write weekly file
        weekly_file.write_text(content)
        
        # Track
        if "weekly_summaries" not in self.tracking:
            self.tracking["weekly_summaries"] = {}
        self.tracking["weekly_summaries"][week_label] = {
            "file": str(weekly_file),
            "entries_consolidated": len(week_entries),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.save_tracking()
        
        return {
            "file": str(weekly_file),
            "week": week_label,
            "entries": len(week_entries)
        }
    
    def query_weekly_memory(self, query):
        """Query weekly consolidated memory."""
        results = []
        for weekly_file in DISTILLED_DIR.glob("Week_*.md"):
            with open(weekly_file, 'r') as f:
                content = f.read()
                if query.lower() in content.lower():
                    results.append({
                        "file": str(weekly_file),
                        "week": weekly_file.stem,
                        "snippet": content[:300]
                    })
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # CONFLICT DETECTION (venv vs conda scenario)
    # ═══════════════════════════════════════════════════════════════
    
    CONFLICT_INDICATORS = [
        ("use", "prefer", "instead"),  # "use conda instead of venv"
        ("instead of", "not", "rather than"),  # "conda rather than venv"
        ("actually", "really", "actually"),  # "actually, we use conda"
        ("change", "update", "switch"),  # "we switched to conda"
    ]
    
    def detect_conflicts(self, query, limit=10):
        """Detect potentially conflicting memories about the same topic."""
        results = self.query(query, limit=limit)
        
        if len(results.get("vectors", [])) < 2:
            return None
        
        conflicts = []
        vectors = results["vectors"]
        
        for i, r1 in enumerate(vectors):
            for r2 in vectors[i+1:]:
                # Check for contradictory language
                c1 = r1["content"].lower()
                c2 = r2["content"].lower()
                
                # Look for opposite patterns
                is_conflict = False
                conflict_type = None
                
                # Detect "instead of" or "rather than" patterns
                for pattern in self.CONFLICT_INDICATORS:
                    if any(p in c1 for p in pattern) and any(p in c2 for p in pattern):
                        if c1 != c2:  # Different content
                            is_conflict = True
                            conflict_type = "contradiction"
                            break
                
                if is_conflict:
                    conflicts.append({
                        "memory_1": r1["content"][:200],
                        "memory_2": r2["content"][:200],
                        "collection_1": r1.get("collection"),
                        "collection_2": r2.get("collection"),
                        "score_1": r1.get("score"),
                        "score_2": r2.get("score"),
                        "conflict_type": conflict_type,
                        "resolution": "ASK_USER"
                    })
        
        return conflicts if conflicts else None
    
    def get_conflict_question(self, conflicts):
        """Generate a clarifying question for the user."""
        if not conflicts:
            return None
        
        c = conflicts[0]
        return f"""⚠️ **Memory Conflict Detected**

I found potentially conflicting memories:

**Memory A**: "{c['memory_1'][:100]}..."
**Memory B**: "{c['memory_2'][:100]}..."

Are these separate contexts (e.g., "venv for apps, conda for data science"), or should I update your preference?"""
    
    # ═══════════════════════════════════════════════════════════════
    # GRACEFUL DEGRADATION (Qdrant fallback)
    # ═══════════════════════════════════════════════════════════════
    
    def query_with_fallback(self, query, include_daily=True, include_weekly=True):
        """Try Qdrant first, fall back to file search if unavailable."""
        try:
            # Try Qdrant + all tiers
            return {
                "source": "qdrant",
                "daily": self.query_daily_memory(query) if include_daily else [],
                "weekly": self.query_weekly_memory(query) if include_weekly else [],
                "vectors": self._vector_search_fallback(query)
            }
        except Exception as e:
            print(f"⚠️ Qdrant unavailable ({e}), falling back to file search...")
            
            # Fall back to file-based search
            return {
                "source": "files",
                "daily": self.query_daily_memory(query) if include_daily else [],
                "weekly": self.query_weekly_memory(query) if include_weekly else [],
                "vectors": self._file_based_search(query)
            }
    
    def _vector_search_fallback(self, query):
        """Normal vector search."""
        vec = self._embed(query)
        results = []
        for coll in COLLECTIONS:
            try:
                resp = self.client.query_points(
                    collection_name=coll, query=vec, limit=5, with_payload=True
                )
                for pt in resp.points:
                    results.append({
                        "collection": coll,
                        "content": pt.payload.get("content", "")[:200],
                        "score": pt.score
                    })
            except:
                continue
        return results
    
    def _file_based_search(self, query):
        """Fallback: grep-based search through memory files."""
        import subprocess
        results = []
        
        # Search daily files
        for md_file in MEMORY_DIR.glob("*.md"):
            if md_file.stem.startswith("Week_"):
                continue  # Skip weekly summaries
            
            try:
                result = subprocess.run(
                    ["grep", "-i", "-n", query, str(md_file)],
                    capture_output=True, text=True
                )
                for line in result.stdout.split("\n")[:3]:  # Limit to 3 matches per file
                    if line.strip():
                        results.append({
                            "collection": "file",
                            "file": str(md_file),
                            "content": line.split(":", 1)[1].strip()[:200] if ":" in line else line.strip()[:200],
                            "score": 0.5  # Lower score for file-based
                        })
            except:
                continue
        
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # ENTITY QUARANTINE (VALIDATION BEFORE PROMOTION)
    # ═══════════════════════════════════════════════════════════════
    
    def quarantine_entity(self, entity_name, context=""):
        """Put a discovered entity in quarantine until validated."""
        quarantine_file = QUARANTINE_DIR / f"{entity_name.lower().replace(' ', '_')}.md"
        
        content = f"""# {entity_name} (IN QUARANTINE)

*Discovered: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
*Status: PENDING VALIDATION*

## Context

{context or "Discovered during conversation."}

## Keywords

- {entity_name}
- {entity_name.lower().replace(' ', '_')}

## Validation

- [ ] Confirm entity exists
- [ ] Determine entity type (person, project, topic)
- [ ] Add to appropriate collection

---

*Auto-generated by MemoryBrain. Must be validated before promotion.*
"""
        
        quarantine_file.write_text(content)
        
        # Track
        self.tracking["quarantine"].append({
            "name": entity_name,
            "file": str(quarantine_file),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending"
        })
        self.save_tracking()
        
        return {
            "entity": entity_name,
            "file": str(quarantine_file),
            "status": "quarantined"
        }
    
    def validate_entity(self, entity_name, target_collection=None, keywords=None):
        """Validate entity and move from quarantine to main collection."""
        quarantine_file = QUARANTINE_DIR / f"{entity_name.lower().replace(' ', '_')}.md"
        
        if not quarantine_file.exists():
            return {"error": "Entity not in quarantine"}
        
        # Move to entities directory
        entities_dir = MEMORY_DIR / "entities"
        entities_dir.mkdir(exist_ok=True)
        
        target_file = entities_dir / f"{entity_name.lower().replace(' ', '_')}.md"
        
        # Update content with validation
        content = quarantine_file.read_text()
        content = content.replace("(IN QUARANTINE)", "(VALIDATED)")
        content += f"\n## Validation Details\n"
        content += f"- Validated: {datetime.now().isoformat()}\n"
        content += f"- Target Collection: {target_collection or 'mem_steven'}\n"
        if keywords:
            content += f"- Keywords: {', '.join(keywords)}\n"
        
        target_file.write_text(content)
        quarantine_file.unlink()  # Remove from quarantine
        
        # Update tracking
        for i, e in enumerate(self.tracking["quarantine"]):
            if e["name"] == entity_name:
                self.tracking["quarantine"].pop(i)
                break
        
        if "validated_entities" not in self.tracking:
            self.tracking["validated_entities"] = []
        self.tracking["validated_entities"].append({
            "name": entity_name,
            "file": str(target_file),
            "collection": target_collection or "mem_steven",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.save_tracking()
        
        # Optionally create Qdrant collection
        if target_collection:
            try:
                self.client.create_collection(
                    collection_name=target_collection,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
            except:
                pass
    
    def prune_old_files(self, retention_days=None):
        """Prune daily files older than retention_days (vectors remain in Qdrant)."""
        if retention_days is None:
            # Load from config
            config_file = Path("/home/vel/.openclaw/memory-system/config/user_config.json")
            if config_file.exists():
                import json
                config = json.load(open(config_file))
                retention_days = config.get("pruning", {}).get("daily_file_retention_days", 7)
            else:
                retention_days = 7
        
        cutoff = datetime.now() - timedelta(days=retention_days)
        pruned = 0
        kept = 0
        
        for md_file in MEMORY_DIR.glob("*.md"):
            if md_file.stem.startswith("Week_"):
                continue  # Skip weekly summaries
            
            try:
                file_date = datetime.strptime(md_file.stem, "%Y-%m-%d")
                if file_date < cutoff:
                    # Archive instead of delete
                    archive_dir = MEMORY_DIR / "archive"
                    archive_dir.mkdir(exist_ok=True)
                    md_file.rename(archive_dir / md_file.name)
                    pruned += 1
                else:
                    kept += 1
            except:
                kept += 1  # Keep files that don't match date pattern
        
        return {"pruned": pruned, "kept": kept}
    
    # ═══════════════════════════════════════════════════════════════
    # ENTITY DISCOVERY
    # ═══════════════════════════════════════════════════════════════
        return {
            "entity": entity_name,
            "file": str(target_file),
            "collection": target_collection or "mem_steven",
            "status": "validated"
        }
    
    def get_quarantine_list(self):
        """Get list of entities in quarantine."""
        return self.tracking.get("quarantine", [])
    
    # ═══════════════════════════════════════════════════════════════
    # KEYWORD TRIGGERS
    # ═══════════════════════════════════════════════════════════════
    
    def detect_memory_trigger(self, text):
        """Detect if user wants to save something to memory."""
        for pattern, importance in MEMORY_TRIGGERS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                return {
                    "content": content,
                    "importance": importance,
                    "detected_trigger": pattern
                }
        return None
    
    def handle_memory_trigger(self, text):
        """Handle a memory trigger - save to daily memory."""
        trigger = self.detect_memory_trigger(text)
        if not trigger:
            return None
        
        # Determine category based on trigger type
        if "decide" in trigger["detected_trigger"]:
            category = "decision"
        elif "action" in trigger["detected_trigger"] or "make sure" in trigger["detected_trigger"]:
            category = "action"
        elif "important" in trigger["detected_trigger"]:
            category = "important"
        else:
            category = "general"
        
        # Save to daily memory
        result = self.save_daily_memory(
            content=trigger["content"],
            importance=trigger["importance"],
            category=category
        )
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # ENTITY DISCOVERY
    # ═══════════════════════════════════════════════════════════════
    
    def discover_entities(self, text):
        """Detect potential new entities in text."""
        import re
        discovered = []
        
        # Look for capitalized phrases
        stop_words = {"I", "We", "You", "He", "She", "It", "They", "The", "A", "An",
                      "This", "That", "These", "Those", "When", "Where", "How", "Why"}
        
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(pattern, text)
        
        for match in matches:
            if match not in stop_words and len(match.split()) <= 4:
                # Check quarantine
                quarantined = [e["name"] for e in self.tracking.get("quarantine", [])]
                validated = [e["name"] for e in self.tracking.get("validated_entities", [])]
                if match not in quarantined and match not in validated:
                    discovered.append(match)
        
        return list(set(discovered))
    
    def auto_discover_and_quarantine(self, text):
        """Discover entities and put them in quarantine."""
        entities = self.discover_entities(text)
        results = []
        for entity in entities:
            result = self.quarantine_entity(entity, text)
            results.append(result)
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS & QUERY
    # ═══════════════════════════════════════════════════════════════
    
    def status(self):
        print(f"\n🧠 Memory Brain - Human-Readable Versioning")
        print(f"=" * 50)
        
        # Count daily files
        daily_count = len(list(MEMORY_DIR.glob("*.md")))
        print(f"Daily memory files: {daily_count}")
        
        # Count weekly summaries
        weekly_count = len(list(DISTILLED_DIR.glob("Week_*.md")))
        print(f"Weekly summaries: {weekly_count}")
        
        # Quarantine status
        quarantine_count = len(self.tracking.get("quarantine", []))
        print(f"Entities in quarantine: {quarantine_count}")
        
        # Validated entities
        validated_count = len(self.tracking.get("validated_entities", []))
        print(f"Validated entities: {validated_count}")
        
        print(f"\nCollections:")
        for coll in COLLECTIONS:
            try:
                info = self.client.get_collection(coll)
                print(f"  {coll}: {info.points_count} points")
            except:
                print(f"  {coll}: unknown")
        
        print(f"\nLast consolidation: {self.tracking.get('last_consolidation', 'Never')}")
    
    def query(self, query, include_daily=True, include_weekly=True, limit=10):
        """Query across all memory tiers."""
        results = {"daily": [], "weekly": [], "vectors": []}
        
        if include_daily:
            results["daily"] = self.query_daily_memory(query)
        
        if include_weekly:
            results["weekly"] = self.query_weekly_memory(query)
        
        # Vector search
        vec = self._embed(query)
        for coll in COLLECTIONS:
            try:
                resp = self.client.query_points(
                    collection_name=coll, query=vec, limit=limit, with_payload=True
                )
                for pt in resp.points:
                    results["vectors"].append({
                        "collection": coll,
                        "content": pt.payload.get("content", "")[:200],
                        "score": pt.score
                    })
            except:
                continue
        
        return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--save", type=str, help="Save to daily memory")
    parser.add_argument("--consolidate-weekly", action="store_true", help="Consolidate to weekly")
    parser.add_argument("--discover", type=str, help="Discover entities in text")
    parser.add_argument("--quarantine-list", action="store_true", help="List quarantined entities")
    parser.add_argument("--validate", type=str, help="Validate entity from quarantine")
    parser.add_argument("--category", type=str, default="general", help="Category for memory")
    args = parser.parse_args()
    
    brain = MemoryBrain()
    
    if args.status:
        brain.status()
    elif args.save:
        result = brain.save_daily_memory(args.save, category=args.category)
        print(f"✅ Saved to {result['file']}")
    elif args.consolidate_weekly:
        result = brain.consolidate_to_weekly()
        if result:
            print(f"✅ Consolidated to {result['file']} ({result['entries']} entries)")
        else:
            print("No daily files to consolidate")
    elif args.discover:
        entities = brain.auto_discover_and_quarantine(args.discover)
        for e in entities:
            print(f"🔒 Quarantined: {e['entity']} → {e['file']}")
    elif args.quarantine_list:
        items = brain.get_quarantine_list()
        print(f"\n🔒 Entities in Quarantine ({len(items)}):")
        for item in items:
            print(f"  - {item['name']} (since {item['timestamp'][:10]})")
    elif args.validate:
        result = brain.validate_entity(args.validate)
        print(f"✅ Validated: {result}")
    elif args.query:
        results = brain.query(args.query)
        print(f"\n🔍 Results for: {args.query}")
        print("=" * 50)
        if results["daily"]:
            print(f"\n📅 Daily ({len(results['daily'])} files):")
            for r in results["daily"][:3]:
                print(f"  - {r['date']}: {r['content_snippet'][:100]}...")
        if results["weekly"]:
            print(f"\n📆 Weekly ({len(results['weekly'])} summaries):")
            for r in results["weekly"][:3]:
                print(f"  - {r['week']}: {r['content_snippet'][:100]}...")
    elif args.prune:
        result = brain.prune_old_files()
        print(f"✅ Pruned {result['pruned']} old daily files")
        print(f"   Kept: {result['kept']} recent files")
    
    elif args.conflicts:
        conflicts = brain.detect_conflicts(args.conflicts)
        if conflicts:
            for c in conflicts[:3]:
                print(f"\n⚠️ CONFLICT ({c['conflict_type']})")
                print(f"   A: {c['memory_1'][:80]}...")
                print(f"   B: {c['memory_2'][:80]}...")
        else:
            print("✅ No conflicts detected")
        
        question = brain.get_conflict_question(conflicts)
        if question:
            print(f"\n{question}")
    
    else:
        print("MemoryBrain - Human-Readable Versioning with Entity Quarantine")
        print()
        print("Commands:")
        print("  --status                    Show status")
        print("  --save 'text'               Save to daily memory")
        print("  --category decision/action  Category for memory")
        print("  --consolidate-weekly        Consolidate daily → weekly")
        print("  --discover 'text'           Discover & quarantine entities")
        print("  --quarantine-list           List quarantined entities")
        print("  --validate 'entity_name'    Validate entity from quarantine")
        print("  --query 'text'              Query all memory tiers")
        print("  --prune                     Prune old daily files")
        print("  --conflicts 'query'         Check for memory conflicts")
