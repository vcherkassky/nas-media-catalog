#!/bin/bash

# End-to-end testing script for NAS Media Catalog (Local Development)

set -e

echo "🧪 Running NAS Media Catalog E2E Tests (Local Environment)"

# Function to cleanup
cleanup() {
    echo "🧹 Cleaning up..."
    # Kill any background processes we started
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Parse command line arguments
MODE="${1:-local}"
HEADED="${2:-false}"

case "$MODE" in        
    "local")
        echo "💻 Running tests against local environment..."
        
        # Check if e2e dependencies are installed
        if [ ! -d "e2e/node_modules" ]; then
            echo "📦 Installing E2E test dependencies..."
            cd e2e
            npm install
            npx playwright install
            cd ..
        fi
        
        # Check if services are running locally
        if ! curl -s http://127.0.0.1:3000 > /dev/null 2>&1; then
            echo "❌ UI service not running on 127.0.0.1:3000"
            echo "   Please start the development environment first:"
            echo "   ./scripts/dev-start.sh"
            exit 1
        fi
        
        if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo "❌ API service not running on 127.0.0.1:8000"
            echo "   Please start the development environment first:"
            echo "   ./scripts/dev-start.sh"
            exit 1
        fi
        
        # Run tests locally
        cd e2e
        export BASE_URL="http://127.0.0.1:3000"
        export API_URL="http://127.0.0.1:8000"
        
        if [ "$HEADED" = "true" ]; then
            echo "🏃 Running Playwright tests in headed mode..."
            npm run test:headed
        else
            echo "🏃 Running Playwright tests..."
            npm test
        fi
        cd ..
        ;;
        
    "ui")
        echo "🎭 Running tests in UI mode..."
        
        # Check if e2e dependencies are installed
        if [ ! -d "e2e/node_modules" ]; then
            echo "📦 Installing E2E test dependencies..."
            cd e2e
            npm install
            npx playwright install
            cd ..
        fi
        
        cd e2e
        export BASE_URL="http://127.0.0.1:3000"
        export API_URL="http://127.0.0.1:8000"
        npm run test:ui
        cd ..
        ;;

    "with-services")
        echo "🚀 Starting services and running tests..."
        
        # Check if services are already running
        if curl -s http://127.0.0.1:3000 > /dev/null 2>&1 || curl -s http://127.0.0.1:8000 > /dev/null 2>&1; then
            echo "❌ Services already running. Please stop them first or use 'local' mode."
            exit 1
        fi
        
        # Check if e2e dependencies are installed
        if [ ! -d "e2e/node_modules" ]; then
            echo "📦 Installing E2E test dependencies..."
            cd e2e
            npm install
            npx playwright install
            cd ..
        fi
        
        # Start API
        echo "🔧 Starting API server..."
        cd api
        if ! command -v uv &> /dev/null; then
            echo "❌ uv not found. Please install uv first."
            exit 1
        fi
        uv run python run_server.py > ../api.log 2>&1 &
        API_PID=$!
        cd ..
        
        # Start UI
        echo "🔧 Starting UI server..."
        cd ui
        if [ ! -d "node_modules" ]; then
            npm install
        fi
        npm start > ../ui.log 2>&1 &
        UI_PID=$!
        cd ..
        
        # Wait for services to be ready
        echo "⏳ Waiting for services to be ready..."
        timeout=60
        while [ $timeout -gt 0 ]; do
            if curl -s http://127.0.0.1:3000 > /dev/null 2>&1 && \
               curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
                echo "✅ Services are ready!"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -le 0 ]; then
            echo "❌ Services failed to start within timeout"
            echo "API log:"
            tail -20 api.log 2>/dev/null || echo "No API log found"
            echo "UI log:"
            tail -20 ui.log 2>/dev/null || echo "No UI log found"
            exit 1
        fi
        
        # Run tests
        cd e2e
        export BASE_URL="http://127.0.0.1:3000"
        export API_URL="http://127.0.0.1:8000"
        
        if [ "$HEADED" = "true" ]; then
            echo "🏃 Running Playwright tests in headed mode..."
            npm run test:headed
        else
            echo "🏃 Running Playwright tests..."
            npm test
        fi
        cd ..
        ;;
        
    *)
        echo "Usage: $0 [local|ui|with-services] [headed]"
        echo ""
        echo "Modes:"
        echo "  local        - Run tests against already running local servers (default)"
        echo "  ui           - Run tests in interactive UI mode"
        echo "  with-services - Start services and run tests, then cleanup"
        echo ""
        echo "Options:"
        echo "  headed       - Run tests in headed mode (show browser)"
        echo ""
        echo "Examples:"
        echo "  $0                    # Run against running local servers"
        echo "  $0 local              # Same as above"
        echo "  $0 local headed       # Run with browser visible"
        echo "  $0 ui                 # Interactive UI mode"
        echo "  $0 with-services      # Start services, test, cleanup"
        exit 1
        ;;
esac

echo ""
echo "✅ E2E tests completed!"

# Show test results if available
if [ -f "e2e/playwright-report/index.html" ]; then
    echo "📊 Test report available at: e2e/playwright-report/index.html"
    echo "   View with: cd e2e && npm run report"
fi

# Cleanup log files
rm -f api.log ui.log 2>/dev/null || true