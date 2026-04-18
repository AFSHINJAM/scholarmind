#!/bin/bash
echo "╔══════════════════════════════════════════╗"
echo "║        ScholarMind - Local Server        ║"
echo "╚══════════════════════════════════════════╝"

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "⚠️  ANTHROPIC_API_KEY not set!"
  echo "   Run: export ANTHROPIC_API_KEY=your-key-here"
  echo "   Get your key at: https://console.anthropic.com"
  echo ""
  read -p "Enter your Anthropic API key now (or press Enter to skip): " key
  if [ -n "$key" ]; then
    export ANTHROPIC_API_KEY=$key
  fi
fi

echo ""
echo "Starting ScholarMind..."
echo "➜ App:  http://localhost:8000"
echo "➜ API:  http://localhost:8000/api"
echo "➜ Docs: http://localhost:8000/docs"
echo ""
echo "Demo login: demo@mcgill.ca / demo1234"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")/backend"
python main.py
