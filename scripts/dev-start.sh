#!/bin/bash

# Development startup script for NAS Media Catalog

set -e

# Configuration
API_PORT=${API_PORT:-8000}
UI_PORT=${UI_PORT:-3000}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help      Show this help message"
    echo "  -c, --cleanup   Only perform cleanup (kill existing processes)"
    echo "  -s, --start     Start services (default behavior)"
    echo "  --api-port      API port (default: 8000, env: API_PORT)"
    echo "  --ui-port       UI port (default: 3000, env: UI_PORT)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start services with cleanup"
    echo "  $0 --cleanup          # Only cleanup existing processes"
    echo "  $0 --start            # Start services with cleanup"
    echo "  $0 --api-port 8001    # Use custom API port"
    echo ""
}

# Function to perform cleanup
cleanup_processes() {
    echo "🧹 Cleaning up existing processes..."
    
    # Kill specific process patterns
    pkill -f "run_server.py" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "node server.js" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
    pkill -f "nas-media-catalog-ui" 2>/dev/null || true
    
    # Kill processes using our specific ports
    for port in $API_PORT $UI_PORT; do
        pid=$(lsof -ti :$port 2>/dev/null || true)
        if [ ! -z "$pid" ]; then
            echo "   Killing process $pid using port $port"
            kill -TERM $pid 2>/dev/null || true
            sleep 1
            # Force kill if still running
            kill -KILL $pid 2>/dev/null || true
        fi
    done
    
    sleep 2  # Give processes time to shut down
    
    # Verify cleanup
    echo "🔍 Verifying cleanup..."
    local cleanup_success=true
    
    for port in $API_PORT $UI_PORT; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "   ⚠️  Port $port is still in use"
            cleanup_success=false
        else
            echo "   ✅ Port $port is free"
        fi
    done
    
    if [ "$cleanup_success" = true ]; then
        echo "✅ Cleanup completed successfully!"
    else
        echo "⚠️  Some processes may still be running. You might need to:"
        echo "   - Check running processes: ps aux | grep -E '(run_server|node.*server)'"
        echo "   - Kill manually: kill <PID>"
        echo "   - Check port usage: lsof -i :$API_PORT -i :$UI_PORT"
    fi
}

# Parse command line arguments
CLEANUP_ONLY=false
START_SERVICES=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--cleanup)
            CLEANUP_ONLY=true
            START_SERVICES=false
            shift
            ;;
        -s|--start)
            START_SERVICES=true
            CLEANUP_ONLY=false
            shift
            ;;
        --api-port)
            API_PORT="$2"
            shift 2
            ;;
        --ui-port)
            UI_PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Show configuration
if [ "$CLEANUP_ONLY" = true ]; then
    echo "🧹 NAS Media Catalog - Cleanup Mode"
else
    echo "🚀 Starting NAS Media Catalog Development Environment"
fi
echo "   API Port: $API_PORT"
echo "   UI Port: $UI_PORT"
echo ""

# Always perform cleanup first
cleanup_processes

# Exit early if cleanup-only mode
if [ "$CLEANUP_ONLY" = true ]; then
    echo ""
    echo "🎯 Cleanup completed. Use '$0 --start' to start services."
    exit 0
fi

# Check if required tools are available
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install uv first."
    echo "   Install uv: pip install uv"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js first."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "❌ curl not found. Please install curl for health checks."
    exit 1
fi

# Check if ports are available
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is still in use by another service after cleanup."
        echo "   You may need to manually stop the service using port $port."
        echo "   Try: lsof -i :$port to see what's using it."
        return 1
    fi
}

# Function to start services
start_services() {
    echo "💻 Starting services..."
    
    # Check required ports
    if ! check_port $API_PORT "API" || ! check_port $UI_PORT "UI"; then
        echo "Please stop the services using these ports and try again."
        exit 1
    fi
    
    # Check if API dependencies are installed
    if [ ! -d "api/.venv" ] && [ ! -f "api/uv.lock" ]; then
        echo "📦 Installing API dependencies..."
        cd api
        uv sync
        cd ..
    fi
    
    # Check if UI dependencies are installed
    if [ ! -d "ui/node_modules" ]; then
        echo "📦 Installing UI dependencies..."
        cd ui
        npm install
        cd ..
    fi
    
    echo "🔧 Starting API server..."
    cd api
    SERVER_PORT=$API_PORT uv run python run_server.py &
    API_PID=$!
    cd ..
    
    echo "🔧 Starting UI server..."
    cd ui
    PORT=$UI_PORT API_BASE_URL=http://127.0.0.1:$API_PORT npm start &
    UI_PID=$!
    cd ..
    
    echo ""
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    
    # Wait for API health check
    local timeout=30
    while [ $timeout -gt 0 ]; do
        if curl -s http://127.0.0.1:$API_PORT/health > /dev/null 2>&1; then
            echo "✅ API is healthy!"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        echo "⚠️  API health check timed out, but services are running"
    fi
    
    # Wait for UI to be ready
    timeout=15
    while [ $timeout -gt 0 ]; do
        if curl -s http://127.0.0.1:$UI_PORT > /dev/null 2>&1; then
            echo "✅ UI is ready!"
            break
        fi
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -le 0 ]; then
        echo "⚠️  UI readiness check timed out, but service is running"
    fi
    
    echo ""
    echo "✅ Services started successfully!"
    echo "   📡 API: http://127.0.0.1:$API_PORT"
    echo "   📡 API Docs: http://127.0.0.1:$API_PORT/docs"
    echo "   🌐 UI: http://127.0.0.1:$UI_PORT"
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Wait for interrupt
    trap 'echo "🛑 Stopping services..."; kill $API_PID $UI_PID 2>/dev/null; exit 0' INT
    wait
}

# Start services
start_services
