#!/usr/bin/env python3
"""
Memory Vectorization - Entity-Centric Collections

Indexes memory files into entity-centric Qdrant collections.
Part of Molting Memory system.
"""

import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from sentence_transformers import SentenceTransformer

# Configuration - configurable via config/user_config.json
CONFIG_FILE = Path(__file__).parent.parent / "config" / "user_config.json"

if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    QDRANT_URL = config.get('qdrant', {}).get('url', 'http://127.0.0.1:6333')
    MEMORY_DIR = Path(config.get('memory', {}).get('dir', '~/.openclaw/memory'))
    EMBEDDING_MODEL = config.get('embedding_model', 'all-MiniLM-L6-v2')
else:
    QDRANT_URL = "http://127.0.0.1:6333"
    MEMORY_DIR = Path(os.path.expanduser("~/.openclaw/memory"))
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Default entity-centric collections
DEFAULT_COLLECTIONS = {
    "mem_steven": {
        "desc": "User preferences, history, context",
        "keywords": ["steven", "user", "preferences", "goals"],
    },
    "mem_kaylie": {
        "desc": "Additional user details",
        "keywords": ["kaylie", "wedding", "partner"],
    },
    "mem_projects": {
        "desc": "Active projects, status, decisions",
        "keywords": ["project", "task", "status", "goal"],
    },
    "mem_velcrafting": {
        "desc": "Business context",
        "keywords": ["business", "client", "revenue", "consulting", "velcrafting"],
    },
    "mem_ren_collective": {
        "desc": "Agent capabilities, decisions",
        "keywords": ["agent", "collective", "decision"],
    },
    "mem_sessions": {
        "desc": "Session transcripts",
        "keywords": ["session", "transcript", "conversation"],
    },
    "mem_distilled": {
        "desc": "Weekly summaries",
        "keywords": ["weekly", "summary", "distilled"],
    },
    "mem_secrets": {
        "desc": "Credentials, API keys",
        "keywords": ["secret", "api", "token", "credential"],
    },
}

_model_cache = None

def get_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache

def get_embedding(text):
    try:
        return get_model().encode([text])[0].tolist()
    except:
        return None

def detect_collection(content, filename, collections=None):
    """Detect which collection a memory should go to."""
    if collections is None:
        collections = DEFAULT_COLLECTIONS
    
    content_lower = content.lower()
    filename_lower = filename.lower()
    
    for coll_name, config in collections.items():
        for kw in config.get("keywords", []):
            if kw in content_lower or kw in filename_lower:
                return coll_name
    
    return "mem_sessions"

def init_collections(client, collections=None):
    if collections is None:
        collections = DEFAULT_COLLECTIONS
    
    for name in collections:
        try:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"✅ {name}")
        except Exception as e:
            if "exists" in str(e).lower():
                print(f"ℹ️ {name} exists")
            else:
                print(f"❌ {name}: {e}")

def parse_memory_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    meta = {
        "source_file": str(filepath),
        "stored_at": datetime.now(timezone.utc).isoformat(),
        "memory_tier": "working",
        "access_count": 0,
    }
    
    fname = filepath.stem
    if len(fname) >= 10 and fname[:4].isdigit():
        meta["date"] = fname[:10]
    
    meta["collection"] = detect_collection(content, fname)
    
    return content, meta

def index_file(client, filepath, collections=None):
    content, meta = parse_memory_file(filepath)
    collection = meta["collection"]
    
    chunk_size = 800
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    points = []
    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        if emb:
            points.append(PointStruct(
                id=f"{filepath.stem}_{i}".__hash__() & 0xFFFFFFFF,
                vector=emb,
                payload={
                    "content": chunk,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    **meta
                }
            ))
    
    if points:
        client.upsert(collection_name=collection, points=points)  # Fixed: upsert, not upsert_points
        print(f"  ✅ {filepath.name} → {collection} ({len(chunks)} chunks)")
        return True
    return False

def index_directory(client, dir_path, collections=None):
    dir_path = Path(dir_path)
    if not dir_path.exists():
        print(f"  ⚠️ {dir_path} not found")
        return 0
    
    files = sorted(dir_path.glob("*.md"))
    print(f"📁 {dir_path.name}: {len(files)} files")
    
    indexed = 0
    for fp in files:
        try:
            if index_file(client, fp, collections):
                indexed += 1
        except Exception as e:
            print(f"  ❌ {fp.name}: {e}")
    
    return indexed

def search_memories(client, query, collection=None, limit=5, collections=None):
    emb = get_embedding(query)
    if not emb:
        print("❌ Could not generate embedding")
        return []
    
    results = []
    colls = [collection] if collection else list(collections.keys() if collections else DEFAULT_COLLECTIONS.keys())
    
    for coll in colls:
        try:
            resp = client.query_points(
                collection_name=coll,
                query=emb,
                limit=limit,
                with_payload=True
            )
            for pt in resp.points:
                results.append((coll, pt))
        except Exception as e:
            print(f"Search error {coll}: {e}")
    
    results.sort(key=lambda x: x[1].score, reverse=True)
    
    print(f"\n🔍 '{query}'")
    print("=" * 60)
    
    for i, (coll, hit) in enumerate(results[:limit]):
        p = hit.payload
        print(f"\n{i+1}. [{coll}] {Path(p.get('source_file', '?')).name}")
        print(f"   Score: {hit.score:.3f} | Tier: {p.get('memory_tier', '?')}")
        if p.get('date'):
            print(f"   📅 {p['date']}")
        print(f"   {p.get('content', '')[:200]}...")
    
    return results

def collection_status(client, collections=None):
    if collections is None:
        collections = DEFAULT_COLLECTIONS
    
    print("\n📊 Collection Status")
    print("=" * 50)
    
    total = 0
    for name, config in collections.items():
        try:
            info = client.get_collection(name)
            count = info.points_count
            total += count
            print(f"{name:25} {count:>6} points  {config['desc']}")
        except Exception as e:
            print(f"{name:25} ERROR")
    
    print(f"\n{'Total':25} {total:>6} points")


def main():
    parser = argparse.ArgumentParser(description="Memory Vectorization - Molting Memory")
    parser.add_argument("--index-all", action="store_true", help="Index all memory dirs")
    parser.add_argument("--index-dirs", nargs="+", help="Index specific directories")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--collection", type=str, help="Filter search to collection")
    parser.add_argument("--status", action="store_true", help="Show collection status")
    parser.add_argument("--reset", action="store_true", help="Reset all collections")
    
    args = parser.parse_args()
    
    client = QdrantClient(url=QDRANT_URL)
    
    try:
        client.get_collections()
        print(f"✅ Connected to Qdrant at {QDRANT_URL}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    if args.status:
        collection_status(client)
        return
    
    if args.reset:
        for name in DEFAULT_COLLECTIONS:
            try:
                client.delete_collection(name)
                print(f"🗑️ Deleted: {name}")
            except:
                pass
        init_collections(client)
        return
    
    init_collections(client)
    
    if args.search:
        search_memories(client, args.search, args.collection)
        return
    
    if args.index_all:
        print("\n📚 Indexing memories...")
        index_directory(client, MEMORY_DIR)
        collection_status(client)
    
    elif args.index_dirs:
        for dir_name in args.index_dirs:
            d = MEMORY_DIR / dir_name
            index_directory(client, d)
    
    print("\n✅ Indexing complete")


if __name__ == "__main__":
    main()
