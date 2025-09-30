"""
==========================================================
 Peristaltic-Pump Calibration Utility · ESP32 · MicroPython
----------------------------------------------------------
• Drives up to four pumps with the correct PWM settings
  for either 5 V or 12 V supply, chosen at run-time
• Streams results to the console **and** appends them to a
  CSV file you choose at the start of the session
==========================================================
"""

import machine, time, os

# -------------------------------------------------------------------------
# 1)  Pin map – adapt to your wiring once and forget about it
# -------------------------------------------------------------------------
PUMP_PINS = {1: 32, 2: 33, 3: 25, 4: 26}

# -------------------------------------------------------------------------
# 2)  Pump “profiles” – frequency & duty ceiling for each supply voltage
#     You can add more entries (e.g. 9 V, 24 V) if you ever need them.
# -------------------------------------------------------------------------
PUMP_PROFILES = {
    12: dict(freq=20_000, max_duty=8191),   # 20 kHz, full 13-bit resolution
     5: dict(freq=10_000, max_duty=8191),   # 10 kHz – gentler for 5 V motors
}

# -------------------------------------------------------------------------
# 3)  Pump driver class
# -------------------------------------------------------------------------
class Pump:
    """
    Wraps one PWM output and exposes start()/stop() in human units:
        duty13 = 0…MAX_DUTY   (13-bit, like Arduino’s analogWrite on ESP32)
    """
    def __init__(self, pin_id, *, freq, max_duty):
        self.max_duty = max_duty

        pin  = machine.Pin(pin_id, machine.Pin.OUT)
        self.pwm = machine.PWM(pin, freq=freq, duty=0)

        print(f"[OK] Pump GPIO{pin_id} → {freq/1000:.0f} kHz, "
              f"range 0…{max_duty}")

    # 0-8191 → 0-65535 for duty_u16()
    @staticmethod
    def _map_13b_to_16b(duty13):                   # const ≈ 8.0
        return duty13 * 8

    def set_speed(self, duty13):
        duty13 = max(0, min(duty13, self.max_duty))
        self.pwm.duty_u16(self._map_13b_to_16b(duty13))

    start = set_speed                 # alias
    def stop(self): self.set_speed(0) # helper

# -------------------------------------------------------------------------
# 4)  Tiny REPL helpers
# -------------------------------------------------------------------------
def ask(prompt, _type=int):
    while True:
        try:
            return _type(input(prompt))
        except (ValueError, TypeError):
            print("Invalid input, try again.")

def choose_filename(pump_id, supply_v):
    default = f"pump{pump_id}_{supply_v}V_calib.csv"
    name = input(f"CSV filename [{default}]: ").strip() or default

    # Write header only if file is new / empty
    size = 0
    try:
        size = os.stat(name)[6]      # bytes
    except OSError:
        pass

    if size == 0:
        with open(name, "w") as f:
            f.write("pwm_duty_0-8191,duration_s,weight_g,flow_gps\n")
        print(f"[NEW] {name} created → CSV header written.")
    else:
        print(f"[APPEND] Logging to existing {name}.")

    return name

# -------------------------------------------------------------------------
# 5)  Main routine
# -------------------------------------------------------------------------
def run_calibration():
    print("\n=== Peristaltic-Pump Calibration ===")

    # ── 1.  Pump ID ──────────────────────────────────────────────────
    while True:
        pid = ask("Pump ID (1-4): ")
        if pid in PUMP_PINS:
            break
        print("Pick 1, 2, 3 or 4…")

    # ── 2.  Supply voltage / profile ────────────────────────────────
    while True:
        supply_v = ask("Pump supply voltage? 5 or 12 V: ")
        if supply_v in PUMP_PROFILES:
            profile = PUMP_PROFILES[supply_v]
            break
        print("Only 5 V and 12 V profiles exist right now – add more in code!")

    pump = Pump(PUMP_PINS[pid], **profile)

    # ── 3.  CSV file ────────────────────────────────────────────────
    csv_file = choose_filename(pid, supply_v)

    # ── 4.  Calibration loop ───────────────────────────────────────
    max_duty = profile["max_duty"]

    while True:
        duty = ask(f"PWM duty 0-{max_duty} (-1 to quit): ")
        if duty == -1:
            break
        if not 0 <= duty <= max_duty:
            print(f"Range is 0…{max_duty}.")
            continue

        duration = ask("Run time (s): ")
        if duration <= 0:
            print("Duration must be > 0.")
            continue

        input("Tare scale, then press <Enter>…")

        # ---- Run pump ----
        print(f"→ {duration}s @ duty {duty}")
        pump.start(duty)
        time.sleep(duration)
        pump.stop()
        print("   stopped.")

        # ---- Record result ----
        weight = ask("Weight (g): ", float)
        flow   = weight / duration if duration else 0.0

        line = f"{duty},{duration},{weight},{flow:.4f}\n"
        print(line.rstrip())                 # console echo

        with open(csv_file, "a") as f:       # append to disk
            f.write(line)

    pump.stop()
    print("Done.  Data saved to ➜", csv_file)

# -------------------------------------------------------------------------
print("\nModule loaded – call  run_calibration()  to begin.\n")
