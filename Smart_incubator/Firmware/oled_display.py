# oled_display.py - Enhanced OLED Display Module
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time

# --- I2C Configuration ---
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21

# --- Display Configuration ---
WIDTH = 128
HEIGHT = 64

class OLEDDisplay:
    def __init__(self):
        """Initialize OLED display."""
        try:
            self.i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400000)
            self.oled = SSD1306_I2C(WIDTH, HEIGHT, self.i2c)
            self.last_update_time = 0
            self.update_interval = 1  # Seconds
        except Exception as e:
            print(f"[ERROR] OLED initialization failed: {e}")
            self.oled = None  # Ensure oled is None if it fails

    def update_display(
        self,
        current_temp,
        set_temp,
        elapsed_minutes,
        cycle_length,
        us_active,
        led_active,
        vib_active,
        tec_state,
        cycle_num,
        correlation  # Added correlation parameter
    ):
        """Update the display with new data, now with correlation."""
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return

        if not self.oled:
            return

        self.oled.fill(0)  # Clear display

        # --- Row 1: Temperature ---
        # Display current temperature, simplified to "23.5C" to avoid overhead
        self.oled.text(f"{current_temp:.1f}C", 0, 0)

        # Display target temperature
        self.oled.text(f"({set_temp:.1f}C)", 80, 0)

        # --- Row 2: Cycle Info & Correlation ---
        self.oled.text(f"Cyc:{cycle_num}", 0, 10)
        try:
            corr_display = f"{float(correlation):.2f}"
        except (ValueError, TypeError):
            corr_display = "--"
        self.oled.text(f"Corr:{corr_display}", 64, 10) # Display correlation

        # --- Row 3: Progress Bar ---
        progress = int((elapsed_minutes / cycle_length) * WIDTH)
        self.oled.rect(0, 20, WIDTH, 8, 1)
        self.oled.fill_rect(0, 20, progress, 8, 1)

        # --- Row 4: Status Indicators ---
        self.oled.text("US:", 0, 32)
        self.oled.text("ON" if us_active else "OFF", 24, 32)
        
        self.oled.text("TEC:", 64, 32)
        self.oled.text("ON" if tec_state else "OFF", 96, 32)

        # --- Row 5 & 6: Detailed Status ---
        self.oled.text(f"Time: {int(elapsed_minutes)}/{cycle_length}m", 0, 44)
        
        # --- Row 7: Component Status (LED/VIB) ---
        led_status = "L:ON" if led_active else "L:OFF"
        vib_status = "V:ON" if vib_active else "V:OFF"
        self.oled.text(led_status, 0, 56)
        self.oled.text(vib_status, 64, 56)

        self.oled.show()
        self.last_update_time = current_time

    def clear(self):
        """Clear the display."""
        if self.oled:
            self.oled.fill(0)
            self.oled.show()

# ---- TEST CODE ----
if __name__ == "__main__":
    display = OLEDDisplay()
    if display.oled:
        print("OLED Display Test")
        display.update_display(25.6, 23.0, 50, 100, 1, 1, 0, 1, 1, 1)
        time.sleep(5)
        display.update_display(31.2, 32.0, 75, 100, 0, 0, 0, 0, 2, 0)
        time.sleep(5)
        display.clear()
        display.oled.text("Test Complete", 10, 30)
        display.oled.show()
    else:
        print("OLED initialization failed, skipping test.")
