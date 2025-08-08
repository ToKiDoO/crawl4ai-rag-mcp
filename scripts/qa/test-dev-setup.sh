#!/bin/bash
set -e

echo "Testing development environment setup..."

# Clean start
echo "1. Cleaning up any existing containers..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml down 2>/dev/null || true

# Start services in background
echo "2. Starting services in background..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Wait for services to be ready
echo "3. Waiting for services to be ready..."
sleep 10

# Check service status
echo "4. Checking service status..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps

# Test watch mode
echo "5. Testing watch mode (this will run in foreground)..."
echo "   Press Ctrl+C to stop watch mode"
docker compose -f docker-compose.yml -f docker-compose.dev.yml watch