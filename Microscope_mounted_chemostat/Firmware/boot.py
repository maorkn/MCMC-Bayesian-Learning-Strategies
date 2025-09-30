# boot.py - ESP32 Boot Configuration for MCMC ESP-C Channel Controller
import gc
import esp
import network

# ESP32 boot optimizations
esp.osdebug(None)  # Turn off vendor OS debug messages
gc.collect()       # Clean up memory

# Configure network in station mode
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

print('=== MCMC ESP-C Boot Sequence ===')
print('Memory free:', gc.mem_free())
print('WiFi MAC:', ':'.join(['%02x' % b for b in wlan.config('mac')]))
print('Boot sequence complete - starting main.py') 