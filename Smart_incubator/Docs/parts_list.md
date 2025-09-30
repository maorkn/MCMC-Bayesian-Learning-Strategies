# Smart Incubator - Bill of Materials (BOM)

**Complete parts list for building the Smart Incubator Platform**

This document provides a detailed bill of materials for constructing the Smart Incubator experimental platform. All components are readily available from standard electronics suppliers.

---

## Overview

The Smart Incubator consists of five main subsystems:
1. **Control & Processing**: ESP32 microcontroller and power management
2. **Temperature Regulation**: Sensors, heater, cooler, and drivers
3. **Stimulus Delivery**: LED and vibration modules with control
4. **Data Storage & Display**: SD card and OLED interface
5. **Mechanical & Assembly**: Housing, mounting, and connections

**Estimated Total Cost:** $180 - $320 USD (depending on component choices and vendors)

---

## 1. Control & Processing

### Microcontroller System

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| ESP32-WROOM-32 Development Board | 240 MHz dual-core, 520 KB SRAM, WiFi/Bluetooth | 1 | $8-12 | NodeMCU-32S or DOIT ESP32 DevKit recommended |
| USB-to-Serial Adapter | CP2102 or CH340 (usually included with dev board) | 1 | Included | For programming and monitoring |
| Micro-USB Cable | Data cable, 1-2m length | 1 | $3-5 | Quality cable important for stable connection |

**Subtotal: $11-17**

### Power Supply

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| 5V Power Supply | 5V 3-5A, USB or barrel connector | 1 | $8-15 | Must provide stable 3-5A for heater/cooler |
| 12V Power Supply | 12V 2-3A (if using 12V actuators) | 1 | $10-18 | Optional, for higher power heater/cooler |
| Voltage Regulator | LM7805 or LM2596 step-down | 1-2 | $2-5 | If voltage conversion needed |
| Power Distribution Board | Breadboard or custom PCB | 1 | $3-10 | For organizing power connections |

**Subtotal: $23-48 (depending on configuration)**

---

## 2. Temperature Regulation System

### Temperature Sensing

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| MAX31865 RTD-to-Digital Converter | SPI interface, breakout board | 1 | $12-18 | Adafruit or generic breakout |
| PT100 RTD Temperature Sensor | Platinum resistance thermometer, 2-wire or 3-wire | 1 | $8-15 | Class A accuracy recommended |
| Reference Resistor | 430Ω ±0.1%, metal film | 1 | $0.50-2 | Critical for accuracy (usually included with MAX31865 breakout) |
| RTD Extension Wire | Silicone insulated, 0.5-1m | 1m | $3-5 | For sensor placement flexibility |

**Subtotal: $24-40**

### Heating System

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| PTC Heating Element | 5V or 12V, 5-15W | 1 | $5-12 | Self-regulating, safe for biological use |
| Heater MOSFET | IRFZ44N or IRLZ44N, N-channel | 1 | $1-3 | Logic-level gate (Vgs < 5V) |
| MOSFET Gate Resistor | 10kΩ, 1/4W | 1 | $0.10 | Pull-down for safety |
| Flyback Diode | 1N4007 or similar, >1A | 1 | $0.20 | Protection for inductive loads |
| Heat Sink | TO-220 compatible, small | 1 | $1-3 | Optional but recommended |

**Subtotal: $7-21**

### Cooling System

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| TEC1 Peltier Cooler | TEC1-12706 or similar, 12V 6A max | 1 | $5-10 | 40×40mm standard size |
| Cooler MOSFET | IRFZ44N or IRLZ44N, N-channel | 1 | $1-3 | Same as heater, logic-level |
| MOSFET Gate Resistor | 10kΩ, 1/4W | 1 | $0.10 | Pull-down for safety |
| Flyback Diode | 1N5408 or similar, 3A | 1 | $0.50 | Higher current for Peltier |
| Heat Sink (Cold Side) | Aluminum, small | 1 | $3-8 | Required for efficient cooling |
| Heat Sink (Hot Side) | Aluminum with fan (optional) | 1 | $5-15 | Fan highly recommended for heat dissipation |
| Thermal Paste | High-conductivity, 1-2g syringe | 1 | $3-6 | Critical for Peltier performance |
| Cooling Fan (optional) | 12V, 40×40mm or 60×60mm | 1 | $3-8 | Improves hot-side heat removal |

**Subtotal: $21-50**

---

## 3. Stimulus Delivery System

### Optical Stimulus (LED)

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| High-Brightness White LED | 5mm or 10mm, 20-50mA, white | 1-3 | $1-3 | 3-5V forward voltage |
| LED Driver MOSFET | 2N7000 or BS170, N-channel | 1 | $0.50-1 | Small signal MOSFET sufficient |
| Current-Limiting Resistor | 100-330Ω, 1/4W | 1 | $0.10 | Calculate for 20-30mA |
| LED Mounting | Holder or custom bracket | 1 | $1-3 | Position for uniform illumination |

**Subtotal: $3-8**

### Mechanical Stimulus (Vibration)

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| Vibration Motor | Coin/disc type, 3V DC | 1 | $1-3 | 10mm or 12mm diameter |
| Motor Driver MOSFET | 2N7000 or BS170, N-channel | 1 | $0.50-1 | Small signal MOSFET sufficient |
| Flyback Diode | 1N4148 or 1N4001 | 1 | $0.10 | Motor protection |
| Motor Mounting | Adhesive or custom bracket | 1 | $1-2 | Secure to culture vessel |

**Subtotal: $3-7**

---

## 4. Data Storage & Display

### SD Card System

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| MicroSD Card Module | SPI interface breakout | 1 | $2-5 | 3.3V and 5V compatible |
| MicroSD Card | 4-32 GB, Class 10 | 1 | $5-12 | Must be formatted as DOS_FAT_32 with MBR |
| Card Extension Cable (optional) | Ribbon or individual wires | 1 | $2-4 | For easier card access |

**Subtotal: $9-21**

### Display System

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| OLED Display | SSD1306, 128×64 pixels, I2C | 1 | $5-12 | 0.96" or 1.3" screen |
| Display Mounting | Adhesive or bracket | 1 | $1-3 | Front panel mounting |

**Subtotal: $6-15**

---

## 5. Mechanical & Assembly

### Enclosure & Mounting

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| Enclosure Box | Plastic project box, 150×100×50mm | 1 | $8-15 | Ventilated for heat dissipation |
| Culture Chamber | Glass or plastic vessel | 1 | $5-20 | Size depends on experiment |
| Insulation Material | Foam or fiberglass, 10-20mm | 1 sheet | $3-8 | Thermal isolation for chamber |
| Mounting Brackets | Aluminum or 3D-printed | 2-4 | $2-8 | Custom or generic L-brackets |
| Thermal Interface Material | Silicone pad or paste | 1 | $3-8 | Between heater/cooler and chamber |

**Subtotal: $21-59**

### Wiring & Connectors

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| Jumper Wires | Male-male, female-female, male-female | 40+ | $3-8 | Assorted set |
| Breadboard (optional) | 830 tie-points | 1 | $3-6 | For prototyping |
| PCB (custom, optional) | Custom design | 1 | $10-30 | For permanent assembly |
| Screw Terminals | 2-position and 3-position blocks | 5-10 | $2-5 | Power and sensor connections |
| Heat Shrink Tubing | Assorted sizes, multicolor | 1 set | $3-6 | Wire protection and organization |
| Cable Ties | Small, various lengths | 20+ | $2-4 | Cable management |
| Electrical Tape | 19mm × 10m roll | 1 | $1-2 | Insulation backup |

**Subtotal: $24-61**

---

## 6. Optional Components

### Enhanced Features

| Component | Specification | Quantity | Approx. Cost | Notes |
|-----------|--------------|----------|--------------|-------|
| WiFi Antenna (external) | 2.4 GHz, SMA connector | 1 | $3-8 | Improved signal if ESP32 has connector |
| Battery Backup | 18650 Li-ion with holder | 1-2 | $10-20 | Optional UPS functionality |
| Voltage/Current Monitor | INA219 or similar I2C module | 1 | $3-8 | Power monitoring |
| Real-Time Clock | DS3231 I2C module | 1 | $3-6 | Accurate timekeeping (ESP32 has RTC) |
| Additional Sensors | pH, humidity, etc. | Variable | $10-50 | Experiment-specific |

**Subtotal (Optional): $29-92**

---

## 7. Tools & Consumables

### Required Tools (if not already available)

| Tool | Purpose | Approx. Cost | Notes |
|------|---------|--------------|-------|
| Soldering Iron | Assembly and connections | $15-50 | Temperature controlled recommended |
| Solder | 60/40 or lead-free, 0.8-1mm | $5-10 | Rosin core |
| Wire Strippers | 22-28 AWG | $8-15 | Precision strippers helpful |
| Multimeter | Voltage, current, resistance | $15-40 | Essential for troubleshooting |
| Screwdriver Set | Phillips and flathead, small | $8-15 | Precision set useful |
| Needle-Nose Pliers | Small, for wire work | $8-12 | General assembly |
| Hot Glue Gun | Strain relief and mounting | $5-10 | Low-temp for electronics |

**Tool Subtotal: $64-152** (one-time investment)

---

## Cost Summary

### Budget Configuration (~$180-220)

**Minimum viable system with generic components:**
- Control & Processing: ~$15
- Temperature System: ~$52
- Stimulus System: ~$6  
- Data & Display: ~$15
- Mechanical & Assembly: ~$45
- **Subtotal: ~$133**
- **With tools (if needed): ~$197-285**

### Standard Configuration (~$250-320)

**Recommended system with quality components:**
- Control & Processing: ~$30
- Temperature System: ~$80
- Stimulus System: ~$12
- Data & Display: ~$30
- Mechanical & Assembly: ~$70
- Optional enhancements: ~$40
- **Subtotal: ~$262**
- **With tools (if needed): ~$326-414**

---

## Purchasing Recommendations

### Preferred Suppliers

**Electronics Components:**
- **Adafruit**: Quality breakout boards, excellent documentation
- **SparkFun**: Reliable components, good tutorials
- **DigiKey / Mouser**: Professional-grade components, fast shipping
- **AliExpress / eBay**: Budget options (allow 2-4 weeks shipping)
- **Amazon**: Quick delivery, good for common items

**Specialized Components:**
- **PT100 sensors**: Omega Engineering, RS Components
- **Peltier modules**: Laird Thermal, generic suppliers
- **Enclosures**: Hammond Manufacturing, BUD Industries

### Money-Saving Tips

1. **Buy kits**: ESP32 starter kits often include breadboard, wires, sensors
2. **Bulk orders**: Purchase multiple MOSFETs, resistors from AliExpress
3. **Reuse components**: Salvage from old electronics when possible
4. **Generic vs. branded**: MAX31865 clones work well for most applications
5. **Timing**: Watch for sales, especially on major electronics suppliers

### Quality Considerations

**Don't Compromise On:**
- **MAX31865 + PT100**: Temperature accuracy critical for experiments
- **Power supply**: Stable power prevents crashes and data loss
- **SD card**: Use reputable brand (SanDisk, Samsung) for reliability
- **Thermal paste**: Good quality ensures efficient heat transfer

**Can Use Budget Options:**
- **Enclosure**: Can use cardboard or 3D-printed case initially
- **Display**: Optional for automated experiments
- **Breadboards and wires**: Generic work fine
- **MOSFETs**: Most N-channel logic-level MOSFETs interchangeable

---

## Component Specifications

### Critical Parameters

**MOSFETs Selection:**
- **Gate threshold voltage**: Vgs(th) < 5V (logic-level)
- **Drain current**: Id > 1A continuous for heater/cooler
- **Power dissipation**: Check with heat sink calculations
- **Recommended**: IRFZ44N, IRLZ44N, IRL540N

**Power Supply Sizing:**
- **ESP32**: ~250 mA typical, 500 mA peak
- **PTC heater**: 1-3A @ 5V or 0.5-1.5A @ 12V
- **Peltier cooler**: Up to 6A @ 12V (typically run at 30-50%)
- **Total**: Recommend 5V 5A supply minimum

**SD Card Requirements:**
- **Format**: DOS_FAT_32 (not exFAT)
- **Partition**: MBR (Master Boot Record)
- **Size**: 4-32 GB (larger cards may have compatibility issues)
- **Speed**: Class 10 or UHS-I for reliable logging

---

## Assembly Notes

### Order of Assembly

1. **Power distribution**: Set up and test power rails first
2. **Microcontroller**: Program ESP32, verify basic operation
3. **Temperature sensing**: Install MAX31865 + PT100, test readings
4. **Display**: Connect OLED, verify I2C communication
5. **SD card**: Format correctly, test read/write
6. **Thermal actuators**: Wire MOSFETs, test PWM control
7. **Stimulus modules**: Add LED and vibration, verify operation
8. **Integration**: Assemble in enclosure, cable management
9. **Calibration**: PID tuning, sensor verification

### Testing Checklist

Before final assembly:
- [ ] Power supply voltages correct (5V, 12V if used)
- [ ] ESP32 can be programmed via USB
- [ ] Temperature sensor reads ambient accurately
- [ ] OLED displays test pattern
- [ ] SD card can be read/written
- [ ] Heater activates with PWM signal
- [ ] Cooler activates with PWM signal  
- [ ] LED brightness controllable
- [ ] Vibration motor operates with pulses
- [ ] All MOSFETs cool during operation
- [ ] No shorts or loose connections

---

## Maintenance & Spares

### Recommended Spare Parts

| Component | Reason | Quantity |
|-----------|--------|----------|
| ESP32 board | Programming errors, static damage | 1 |
| PT100 sensor | Physical damage, calibration drift | 1 |
| MOSFETs (assorted) | Most likely to fail component | 3-5 |
| SD cards | Corruption, wear-out | 2 |
| Peltier module | Can degrade over time | 1 |
| Jumper wires | Break during prototyping | 10-20 |

**Spares Kit Cost: ~$30-50**

### Consumables

Expected lifetime and replacement:
- **Thermal paste**: Reapply every 6-12 months
- **SD cards**: Replace if errors detected, backup data regularly
- **PT100 sensor**: Recalibrate annually, replace if drift >0.5°C
- **Peltier module**: 2-5 years typical lifespan with proper cooling
- **PTC heater**: Very long lifetime (>10 years typical)

---

## Version History

**v1.0** (September 2025)
- Initial BOM for Smart Incubator Platform
- Based on ESP32-WROOM-32 architecture
- Dual thermal actuator design
- Multi-modal stimulus capability

---

## Additional Resources

### Datasheets
- ESP32-WROOM-32: [Espressif](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf)
- MAX31865: [Analog Devices](https://www.analog.com/media/en/technical-documentation/data-sheets/max31865.pdf)
- IRFZ44N MOSFET: [International Rectifier/Infineon](https://www.infineon.com/dgdl/irfz44npbf.pdf?fileId=5546d462533600a40153563b3a9f220d)
- TEC1-12706: Various manufacturers, check supplier specifications

### Online Resources
- **MicroPython Documentation**: https://docs.micropython.org/
- **ESP32 Arduino Core**: https://github.com/espressif/arduino-esp32
- **Adafruit Learning**: https://learn.adafruit.com/
- **SparkFun Tutorials**: https://learn.sparkfun.com/

### Community Support
- **ESP32 Forums**: https://esp32.com/
- **MicroPython Forum**: https://forum.micropython.org/
- **Reddit r/esp32**: https://www.reddit.com/r/esp32/

---

## Safety Warnings

⚠️ **Important Safety Considerations:**

1. **Electrical Safety**:
   - Always disconnect power before making connections
   - Use proper insulation on all exposed conductors
   - Check for shorts with multimeter before powering on
   - Use appropriate fuses in power supply lines

2. **Thermal Safety**:
   - Peltier modules can get extremely hot (>100°C)
   - Always use heat sinks and thermal monitoring
   - Do not touch Peltier or heater during operation
   - Ensure adequate ventilation in enclosure

3. **Biological Safety**:
   - Follow biosafety protocols for your organism
   - Sterilize culture-facing components appropriately
   - Ensure electrical isolation from culture media
   - Have contamination protocols in place

4. **Fire Safety**:
   - Never leave unattended during initial testing
   - Use fire-resistant enclosure materials
   - Have CO2 or appropriate extinguisher nearby
   - Install temperature cutoff failsafes

---

**Document maintained by:** Smart Incubator Platform Development Team  
**Last updated:** September 2025  
**For questions or updates:** See repository documentation
