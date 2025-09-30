# main.py - MCMC ESP-C Channel Controller Entry Point
# This file is automatically executed after boot.py on ESP32 startup

try:
    from esp_c_controller import main
    main()
except Exception as e:
    print(f"[FATAL] ESP-C Controller failed to start: {e}")
    import time
    import machine
    
    # Blink LED to indicate error
    try:
        led = machine.Pin(2, machine.Pin.OUT)
        for _ in range(20):
            led.on()
            time.sleep(0.2)
            led.off()
            time.sleep(0.2)
    except:
        pass
    
    # Reset after error indication
    print("[FATAL] Resetting ESP32 in 5 seconds...")
    time.sleep(5)
    machine.reset() 