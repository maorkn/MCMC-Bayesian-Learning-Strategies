# wifi_setup.py - WiFi Access Point Setup for Smart Incubator
import network
import machine
import ubinascii
import time
import gc

def get_unique_device_id():
    """Get a unique device identifier from ESP32's MAC address."""
    mac = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
    return mac[-4:].upper()

def create_ap(device_name=None, password="incubator123"):
    """Create a WiFi Access Point with a unique SSID."""
    gc.collect()
    
    ap = network.WLAN(network.AP_IF)
    
    # Deactivate first to ensure clean state
    ap.active(False)
    time.sleep(0.3)
    gc.collect()
    
    # Generate unique SSID
    device_id = get_unique_device_id()
    ssid = f"Inc-{device_name or device_id}"
    
    # Activate AP
    ap.active(True)
    time.sleep(0.5)
    
    # Configure AP settings
    ap.config(essid=ssid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)
    
    # Wait for AP to become active
    timeout = 10
    start = time.time()
    while not ap.active():
        if time.time() - start > timeout:
            raise Exception("AP timeout")
        time.sleep(0.1)
    
    ip = ap.ifconfig()[0]
    
    print(f"\nWiFi: {ssid} | Pass: {password} | IP: {ip}\n")
    
    gc.collect()
    return ap, ssid, ip

def stop_ap(ap):
    """Stop the WiFi Access Point."""
    if ap:
        try:
            ap.active(False)
        except:
            pass
