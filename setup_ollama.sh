#!/usr/bin/env bash
# Set up local embedding retrieval for the Bilingual Quality Harness.
# Replaces the modelled Canadian-French lexicon gap with real dense retrieval.
set -euo pipefail

MODEL="${1:-bge-m3}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Installing Ollama…"
  if command -v brew >/dev/null 2>&1; then
    brew install ollama
  else
    echo "Homebrew not found. Install Ollama from https://ollama.com/download"
    exit 1
  fi
fi

if ! curl -sf --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Starting ollama serve in the background…"
  (ollama serve >/tmp/ollama.log 2>&1 &)
  for _ in $(seq 1 30); do
    curl -sf --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "Pulling $MODEL (multilingual; strong on French)…"
ollama pull "$MODEL"

echo
echo "Ready. Run:"
echo "  python3 bqh/harness.py --retriever embedding --report report_embed.html"
