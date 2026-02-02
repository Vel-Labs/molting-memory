#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# MOLTING MEMORY - ONE-LINE INSTALL
# ═══════════════════════════════════════════════════════════════
#
# Usage (while your agent is online):
#   curl -sSL https://raw.githubusercontent.com/Vel-Labs/molting-memory/main/install.sh | bash
#
# This script:
#   1. Clones/installs the memory system
#   2. Installs dependencies
#   3. Sets up directory structure
#   4. Downloads Qdrant binary
#   5. Starts Qdrant
#   6. Runs onboarding (agent will guide you)
#
# ═══════════════════════════════════════════════════════════════

set -e

echo "🧠 Installing Molting Memory..."
echo "======================================"

# Detect OS
OS=$(uname -s)
if [[ "$OS" == "Darwin" ]]; then
    QDRANT_URL="https://qdrant.io/releases/latest/download/qdrant-x86_64-apple-darwin.tar.gz"
elif [[ "$OS" == "Linux" ]]; then
    QDRANT_URL="https://qdrant.io/releases/latest/download/qdrant-x86_64-unknown-linux-musl.tar.gz"
else
    echo "❌ Unsupported OS: $OS"
    exit 1
fi

# 1. Clone or update memory system
if [[ -d ".memory-system" ]]; then
    echo "📦 Updating existing installation..."
    cd .memory-system
    git pull origin main 2>/dev/null || echo "⚠️  Could not update, using existing files"
else
    echo "📦 Cloning Molting Memory..."
    git clone https://github.com/Vel-Labs/molting-memory.git .memory-system 2>/dev/null || {
        echo "⚠️  Git clone failed, creating directory structure..."
        mkdir -p .memory-system/{scripts,config,examples/memory}
    }
fi

# 2. Install Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m venv .memory-system/.venv 2>/dev/null || true
source .memory-system/.venv/bin/activate
pip install -q qdrant-client sentence-transformers

# 3. Create memory directory
echo "📁 Creating memory directory..."
mkdir -p memory/{entities,users,decisions,reports,distilled}

# 4. Download and install Qdrant
echo "⬇️  Installing Qdrant..."
cd /tmp
if [[ ! -f qdrant ]]; then
    curl -sSL "$QDRANT_URL" -o qdrant.tar.gz
    tar xzf qdrant.tar.gz
fi
cd - > /dev/null
cp /tmp/qdrant .memory-system/ 2>/dev/null || true
chmod +x .memory-system/qdrant 2>/dev/null || true

# 5. Start Qdrant
echo "🚀 Starting Qdrant..."
.memory-system/qdrant --uri http://127.0.0.1:6333 > /dev/null 2>&1 &
sleep 2

# Verify Qdrant is running
if curl -s http://127.0.0.1:6333/collections > /dev/null 2>&1; then
    echo "✅ Qdrant is running at http://127.0.0.1:6333"
else
    echo "⚠️  Qdrant startup detected - you may need to start it manually"
fi

# 6. Index example memory
echo "📚 Indexing example memory..."
cd .memory-system
source .venv/bin/activate
python scripts/vectorize.py --index-all 2>/dev/null || echo "⚠️  Indexing skipped (no memory files yet)"

# 7. Run onboarding (agent will guide you)
echo ""
echo "======================================"
echo "✅ Installation complete!"
echo "======================================"
echo ""
echo "Your agent will now guide you through setup."
echo "Answer the questions to personalize your memory system."
echo ""
echo "📋 NEXT STEP:"
echo "   Tell your agent: 'Run memory onboarding'"
echo ""
echo "Resources:"
echo "  - Concept Guide: https://docs.google.com/document/d/1eQDmLjwr3oLQgKRLDSHwmw13YaLjCR0V-FAIB07pzn8/edit"
echo "  - Full Docs: https://github.com/Vel-Labs/molting-memory"
echo ""
echo "🪝 CLAW TO ACTION: Try it, share it, if you like it ⭐ star the repo!"
echo "======================================"
