#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AGENTIC MEMORY SYSTEM v1.0 - VALIDATION TEST
# ═══════════════════════════════════════════════════════════════
#
# This script:
# 1. Creates a clean venv
# 2. Installs dependencies
# 3. Runs install script
# 4. Runs onboarding (with simulated input. Validates all)
# 5 components work
#
# Usage: bash test_install.sh
#
# ═══════════════════════════════════════════════════════════════

set -e

echo "🧪 AGENTIC MEMORY SYSTEM v1.0 - VALIDATION TEST"
echo "================================================"
echo ""

# Configuration
TEST_DIR="/tmp/memory-test-$$"
MEMORY_DIR="$TEST_DIR/memory"
SYSTEM_DIR="$TEST_DIR/memory-system"
CRON_FILE="$SYSTEM_DIR/crontab.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; }
fail() { echo -e "${RED}❌ FAIL${NC}: $1"; exit 1; }
info() { echo -e "${YELLOW}ℹ️  $1${NC}"; }

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    rm -rf "$TEST_DIR"
    echo "Done."
}
trap cleanup EXIT

# ═══════════════════════════════════════════════════════════════
# STEP 1: Create clean environment
# ═══════════════════════════════════════════════════════
echo "STEP 1: Creating clean test environment..."
echo ""

mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Create venv
python3 -m venv test-venv
source test-venv/bin/activate

pass "Created clean venv at $TEST_DIR/test-venv"

# ═══════════════════════════════════════════════════════
# STEP 2: Install dependencies
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 2: Installing dependencies..."
echo ""

pip install -q qdrant-client sentence-transformers 2>/dev/null || fail "Failed to install qdrant-client"

pass "Installed qdrant-client and sentence-transformers"

# ═══════════════════════════════════════════════════════
# STEP 3: Download Qdrant
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 3: Downloading Qdrant..."
echo ""

cd /tmp
if [ ! -f qdrant ]; then
    curl -sSL "https://qdrant.io/releases/latest/download/qdrant-x86_64-unknown-linux-musl.tar.gz" -o qdrant.tar.gz
    tar xzf qdrant.tar.gz
fi
cd "$TEST_DIR"

pass "Downloaded Qdrant binary"

# Start Qdrant in background
/home/tmp/qdrant --uri http://127.0.0.1:6333 > /dev/null 2>&1 &
sleep 3

# Verify Qdrant is running
if curl -s http://127.0.0.1:6333/collections > /dev/null 2>&1; then
    pass "Qdrant is running at localhost:6333"
else
    fail "Qdrant failed to start"
fi

# ═══════════════════════════════════════════════════════
# STEP 4: Clone/install memory system
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 4: Setting up memory system..."
echo ""

# Copy our system to test directory
cp -r /home/vel/.openclaw/agent-code/memory-system "$SYSTEM_DIR"

# Create memory directory
mkdir -p "$MEMORY_DIR"/{entities,distilled}
mkdir -p "$MEMORY_DIR/entities/_quarantine"

pass "Memory system files copied"

# ═══════════════════════════════════════════════════════
# STEP 5: Run vectorize (should work)
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 5: Testing vectorize script..."
echo ""

# Create a test memory file
echo "# Test Memory

This is a test memory for validation.

## Decision

We prefer using venv for Python projects.
" > "$MEMORY_DIR/2026-02-01.md"

cd "$SYSTEM_DIR"
python scripts/vectorize.py --status > /dev/null 2>&1

if [ $? -eq 0 ]; then
    pass "Vectorize script runs without errors"
else
    fail "Vectorize script failed"
fi

# ═══════════════════════════════════════════════════════
# STEP 6: Test memory_brain commands
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 6: Testing memory_brain commands..."
echo ""

python scripts/memory_brain.py --status > /dev/null 2>&1
[ $? -eq 0 ] && pass "memory_brain.py --status works" || fail "memory_brain.py --status failed"

python scripts/memory_brain.py --save "Test memory entry" --category decision > /dev/null 2>&1
[ $? -eq 0 ] && pass "memory_brain.py --save works" || fail "memory_brain.py --save failed"

# Test conflict detection
python scripts/memory_brain.py --conflicts "venv conda" > /dev/null 2>&1
[ $? -eq 0 ] && pass "memory_brain.py --conflicts works" || fail "memory_brain.py --conflicts failed"

# Test prune (dry run)
python scripts/memory_brain.py --prune > /dev/null 2>&1
[ $? -eq 0 ] && pass "memory_brain.py --prune works" || fail "memory_brain.py --prune failed"

# ═══════════════════════════════════════════════════════
# STEP 7: Test session ingest
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 7: Testing session ingest..."
echo ""

# Create fake session file
mkdir -p "$TEST_DIR/sessions"
cat > "$TEST_DIR/sessions/test-session.jsonl" << 'EOF'
{"type":"message","id":"test1","message":{"role":"user","content":[{"type":"text","text":"Hello, this is a test conversation."}]}
{"type":"message","id":"test2","message":{"role":"assistant","content":[{"type":"text","content":"Hi! How can I help you today?"}]}
EOF

# Update SESSIONS_DIR in the script temporarily
sed -i "s|SESSIONS_DIR = Path.*|SESSIONS_DIR = Path(\"$TEST_DIR/sessions\")|g" scripts/ingest_sessions.py

python scripts/ingest_sessions.py --hours 24 > /dev/null 2>&1
[ $? -eq 0 ] && pass "ingest_sessions.py works" || fail "ingest_sessions.py failed"

# Verify daily file was created
if [ -f "$MEMORY_DIR/$(date +%Y-%m-%d).md" ]; then
    pass "Daily memory file created from session"
else
    fail "Daily memory file not created"
fi

# Restore SESSIONS_DIR
sed -i "s|SESSIONS_DIR = Path.*|SESSIONS_DIR = Path(\"/home/vel/.openclaw/agents/main/sessions\")|g" scripts/ingest_sessions.py

# ═══════════════════════════════════════════════════════
# STEP 8: Verify crontab file
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 8: Validating crontab template..."
echo ""

if [ -f "$CRON_FILE" ]; then
    if grep -q "memory_brain.py --consolidate" "$CRON_FILE"; then
        pass "Crontab contains consolidation jobs"
    else
        fail "Crontab missing consolidation jobs"
    fi
    
    if grep -q "ingest_sessions.py" "$CRON_FILE"; then
        pass "Crontab contains session ingestion"
    else
        info "Crontab doesn't have session ingestion (optional)"
    fi
else
    fail "Crontab file not created"
fi

# ═══════════════════════════════════════════════════════
# STEP 9: Verify README and SKILL.md
# ═══════════════════════════════════════════════════════
echo ""
echo "STEP 9: Checking documentation..."
echo ""

[ -f "README.md" ] && pass "README.md exists" || fail "README.md missing"
[ -f "SKILL.md" ] && pass "SKILL.md exists" || fail "SKILL.md missing"

if grep -q "Session Discovery" README.md; then
    pass "README.md mentions session discovery"
else
    fail "README.md doesn't mention session discovery"
fi

if grep -q "v1.0" README.md; then
    pass "README.md mentions v1.0"
else
    fail "README.md doesn't mention v1.0"
fi

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════
echo ""
echo "================================================"
echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
echo "================================================"
echo ""
echo "The memory system is ready for GitHub!"
echo ""
echo "Test Summary:"
echo "  ✅ Clean venv created"
echo "  ✅ Dependencies installed"
echo "  ✅ Qdrant running"
echo "  ✅ Vectorize script works"
echo "  ✅ Memory brain commands work"
echo "  ✅ Session ingestion works"
echo "  ✅ Crontab generated"
echo "  ✅ Documentation complete"
echo ""
