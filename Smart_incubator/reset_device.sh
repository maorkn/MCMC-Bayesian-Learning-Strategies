#!/bin/bash
# Quick script to reset the ESP32 device before deployment

PORT="/dev/tty.usbserial-0001"

echo "🔄 Resetting ESP32 device..."
echo ""
echo "This will:"
echo "  1. Stop any running programs"
echo "  2. Perform a hard reset"
echo "  3. Wait for device to boot up"
echo ""

# Try to reset using mpremote
echo "Sending reset command..."
mpremote connect $PORT reset 2>/dev/null &
RESET_PID=$!

# Wait a moment for the reset command
sleep 2

# Kill the reset process if it's still running
kill $RESET_PID 2>/dev/null

echo ""
echo "✅ Reset command sent!"
echo ""
echo "Waiting 5 seconds for device to boot..."
sleep 5

echo ""
echo "✅ Device should be ready now!"
echo ""
echo "Next step: Run the deployment script"
echo "  python3 Smart_incubator/sync_firmware.py"
echo ""
