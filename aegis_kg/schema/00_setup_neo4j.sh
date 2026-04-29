#!/bin/bash

# Phase 1 Knowledge Graph - Neo4j Setup Script
# AEGIS Methodology - Phase 1 Implementation
# Week 1, Day 1-2: Infrastructure Setup

set -e

# Configuration
NEO4J_VERSION="5.16.0"
NEO4J_PASSWORD="neo4j_password"
NEO4J_HTTP_PORT="7474"
NEO4J_BOLT_PORT="7687"
NEO4J_CONTAINER_NAME="aegis-phase1-kg"
NEO4J_NETWORK="aegis-kg-network"

echo "========================================"
echo "AEGIS Phase 1 KG - Neo4j Setup"
echo "========================================"
echo ""
echo "Configuration:"
echo "Neo4j Version: ${NEO4J_VERSION}"
echo "HTTP Port: ${NEO4J_HTTP_PORT}"
echo "Bolt Port: ${NEO4J_BOLT_PORT}"
echo "Container Name: ${NEO4J_CONTAINER_NAME}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER_NAME}$"; then
    echo "Warning: Container ${NEO4J_CONTAINER_NAME} already exists"
    read -p "Do you want to remove the existing container and recreate? (y/n): " -n 1 -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting..."
        exit 0
    fi
    echo "Removing existing container..."
    docker rm -f "${NEO4J_CONTAINER_NAME}"
fi

# Create Docker network if it doesn't exist
if ! docker network ls | grep -q "^${NEO4J_NETWORK}$"; then
    echo "Creating Docker network: ${NEO4J_NETWORK}"
    docker network create ${NEO4J_NETWORK}
fi

# Run Neo4j container
echo "Starting Neo4j container..."
docker run -d \
    --name ${NEO4J_CONTAINER_NAME} \
    --network ${NEO4J_NETWORK} \
    -p ${NEO4J_HTTP_PORT}:${NEO4J_HTTP_PORT} \
    -p ${NEO4J_BOLT_PORT}:${NEO4J_BOLT_PORT} \
    -e NEO4J_AUTH=neo4j/${NEO4J_PASSWORD} \
    -e NEO4J_PLUGINS=["apoc"] \
    -v $(pwd)/data:/data \
    neo4j:${NEO4J_VERSION}

# Wait for Neo4j to start
echo "Waiting for Neo4j to start..."
sleep 10

# Check if container is running
if ! docker ps | grep -q "^${NEO4J_CONTAINER_NAME}$"; then
    echo "Error: Neo4j container failed to start"
    echo "Check logs: docker logs ${NEO4J_CONTAINER_NAME}"
    exit 1
fi

# Test connection to Neo4j
echo "Testing Neo4j connection..."
max_attempts=5
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:${NEO4J_HTTP_PORT} > /dev/null 2>&1; then
        echo "OK: Neo4j is accessible at http://localhost:${NEO4J_HTTP_PORT}"
        break
    fi

    echo "Attempt $attempt of $max_attempts..."
    sleep 3
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "Error: Could not connect to Neo4j after $max_attempts attempts"
    echo "Check logs: docker logs ${NEO4J_CONTAINER_NAME}"
    exit 1
fi

# Print connection information
echo ""
echo "========================================"
echo "Neo4j Setup Complete!"
echo "========================================"
echo ""
echo "Connection Information:"
echo "Neo4j Browser: http://localhost:${NEO4J_HTTP_PORT}"
echo "Bolt URL: bolt://localhost:${NEO4J_BOLT_PORT}"
echo "Username: neo4j"
echo "Password: ${NEO4J_PASSWORD}"
echo ""
echo "Next Steps:"
echo "1. Verify schema: cat 01_create_schema.cypher"
echo "2. Load data: ../etl/01_load_data.py (coming soon)"
echo "3. Verify data: ../validation/01_validate_data.py (coming soon)"
echo ""
echo "Ready for Phase 1 implementation!"
