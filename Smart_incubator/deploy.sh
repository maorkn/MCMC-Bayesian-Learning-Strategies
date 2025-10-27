#!/bin/bash
# Smart Incubator Firmware Deployment Script
# Usage: ./deploy.sh [port] [mode]
# Example: ./deploy.sh /dev/tty.usbserial-0001 full

# Configuration
PORT=${1:-/dev/tty.usbserial-0001}  # Default port
MODE=${2:-core}  # Options: core, full, config-only

echo "🔧 Smart Incubator Deployment"
echo "============================="
echo "Port: $PORT"
echo "Mode: $MODE"
echo ""

# Check if device is connected
if ! ls $PORT &> /dev/null; then
    echo "❌ Error: Device not found at $PORT"
    echo "Available ports:"
    ls /dev/tty.* 2>/dev/null || echo "No USB devices found"
    exit 1
fi

# Function to upload with ampy
upload_ampy() {
    echo "📤 Uploading $1 → $2"
    ampy --port $PORT put "$1" "$2" || echo "⚠️  Warning: Failed to upload $1"
}

# Core HES modules (always deploy these)
if [[ "$MODE" == "core" ]] || [[ "$MODE" == "full" ]]; then
    echo ""
    echo "📦 Deploying Core HES Modules..."
    upload_ampy "Firmware/markovian_hes_executor.py" "/markovian_hes_executor.py"
    upload_ampy "Firmware/hes_config_loader.py" "/hes_config_loader.py"
    upload_ampy "Firmware/hes_transition_engine.py" "/hes_transition_engine.py"
    upload_ampy "Firmware/hes_actuator_controller.py" "/hes_actuator_controller.py"
    upload_ampy "Firmware/hes_logger.py" "/hes_logger.py"
fi

# Full firmware update (existing modules)
if [[ "$MODE" == "full" ]]; then
    echo ""
    echo "📦 Deploying Full Firmware..."
    upload_ampy "Firmware/main.py" "/main.py"
    upload_ampy "Firmware/boot.py" "/boot.py"
    upload_ampy "Firmware/temp_controller.py" "/temp_controller.py"
    upload_ampy "Firmware/led_control.py" "/led_control.py"
    upload_ampy "Firmware/us_control.py" "/us_control.py"
    upload_ampy "Firmware/sd_logger.py" "/sd_logger.py"
    upload_ampy "Firmware/oled_display.py" "/oled_display.py"
    upload_ampy "Firmware/tec.py" "/tec.py"
    upload_ampy "Firmware/heater.py" "/heater.py"
    # Add more existing files as needed
fi

# Configuration files
if [[ "$MODE" == "config-only" ]] || [[ "$MODE" == "full" ]]; then
    echo ""
    echo "📦 Deploying Configuration Files..."
    
    # Check if Configs directory exists
    if [ -d "Configs" ]; then
        for config in Configs/*.json; do
            if [ -f "$config" ]; then
                filename=$(basename "$config")
                upload_ampy "$config" "/sd/$filename"
            fi
        done
    else
        echo "⚠️  No Configs directory found"
    fi
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Connect to REPL: screen $PORT 115200"
echo "2. Or use: mpremote connect $PORT repl"
echo "3. Run experiment: import markovian_hes_executor"
echo ""
