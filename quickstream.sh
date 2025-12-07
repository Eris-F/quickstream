#!/bin/bash
# QuickStream launcher script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

case "${1:-}" in
    start)
        echo "Starting QuickStream server..."
        python server.py
        ;;
    test)
        echo "Running tests..."
        python -m pytest test_server.py -v
        ;;
    install)
        echo "Installing dependencies..."
        pip install -r requirements.txt
        ;;
    *)
        echo "QuickStream - Simple LAN Screen Streaming"
        echo ""
        echo "Usage: $0 {start|test|install}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the streaming server"
        echo "  test    - Run the test suite"
        echo "  install - Install dependencies"
        echo ""
        echo "Or run directly: python server.py"
        exit 1
        ;;
esac
