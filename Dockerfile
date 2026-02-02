# ═══════════════════════════════════════════════════════════════
# AGENTIC MEMORY SYSTEM v1.0 - Docker Test
# ═══════════════════════════════════════════════════════════════
#
# Build and run:
#   docker build -t memory-test .
#   docker run -it --rm memory-test
#
# ═══════════════════════════════════════════════════════════════

FROM python:3.12-slim

WORKDIR /app

# Install Qdrant
RUN apt-get update && apt-get install -y curl && \
    curl -L https://qdrant.io/releases/latest/download/qdrant-x86_64-unknown-linux-musl.tar.gz -o /tmp/qdrant.tar.gz && \
    tar xzf /tmp/qdrant.tar.gz -C /usr/local/bin && \
    rm /tmp/qdrant.tar.gz

# Copy memory system
COPY . /app/memory-system

# Install Python deps
RUN pip install --no-cache-dir qdrant-client sentence-transformers

# Create directories
RUN mkdir -p /app/memory /app/memory/entities /app/memory/distilled /app/memory/entities/_quarantine /app/sessions

# Start Qdrant in background
CMD qdrant --uri http://127.0.0.1:6333 &

# Run tests
WORKDIR /app/memory-system
CMD bash test_install.sh
