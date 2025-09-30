# Microscope Mounted Chemostat - Parts List

Complete bill of materials for building the MCMC platform.

## Electronics Components

### Microcontroller
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| ESP32-WROOM-32 Development Board | 240 MHz dual-core, WiFi/Bluetooth | 1 | Main controller |
| USB Cable (Micro-B or Type-C) | Data + Power capable | 1 | For programming and power |

### Power Supply
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| 12V DC Power Supply | 12V, 2-3A minimum | 1 | For peristaltic pumps |
| Power Jack Adapter | 5.5mm x 2.1mm | 1 | DC barrel jack |
| Step-down Converter (optional) | 12V to 5V, 2A | 1 | If not using USB power for ESP32 |

### MOSFETs and Drivers
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| IRL44ZN N-Channel MOSFET | Logic-level, 60V, 47A | 5 | 4 for pumps, 1 for LED |
| 10kΩ Resistors | 1/4W | 5 | Pull-down for MOSFET gates |
| 1N4007 Diodes | 1A, 1000V | 5 | Flyback protection |

### PCB Components
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| Screw Terminal Blocks | 2-position, 5mm pitch | 6 | For pump/LED connections |
| Header Pins | 2.54mm pitch, male | 40 pins | For ESP32 mounting |
| Female Headers | 2.54mm pitch | 40 pins | ESP32 socket (optional) |

## Pumps and Fluidics

### Peristaltic Pumps
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| 12V Peristaltic Pump | Variable speed, 0-100 ml/min | 4 | DC motor driven |
| Pump Tubing | Silicone, 3mm ID | 2m | For each pump |
| Pump Head | Compatible with tubing | 4 | Usually included with pump |

**Recommended Pump Models:**
- Longer Precision Pump BT100-1L
- Kamoer KCP-PRO series
- Generic 12V peristaltic dosing pump

### Tubing and Connectors
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| Silicone Tubing | 3mm ID, 5mm OD | 5m | Main fluid lines |
| Luer Lock Connectors | Male/Female | 10 | For connections |
| T-Connectors | 3mm barb | 4 | For mixing points |
| Check Valves | 3mm barb, one-way | 4 | Prevent backflow |
| Tubing Clamps | Adjustable | 8 | For setup and maintenance |

## Chamber and Microscopy

### Culture Chamber
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| Glass Microscope Slide | 75mm x 25mm | 2 | Top and bottom |
| Silicone Spacer | Custom cut, 1-2mm thick | 1 | Chamber walls |
| Inlet/Outlet Ports | Luer lock compatible | 4 | Chamber connections |

**Note:** 3D-printed chamber available in `Hardware/3D_Models/`

### Illumination
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| White LED Array | 12V, high power | 1 | PWM controlled |
| LED Heatsink | Aluminum, 40mm | 1 | For LED cooling |
| Thermal Paste | Standard | 1 tube | LED mounting |

### Microscope Integration
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| USB Microscope Camera | 640×480 minimum | 1 | For Cellpose (optional) |
| Camera Mount | Custom or universal | 1 | Align with chamber |

## 3D Printed Components

All STL files available in `Hardware/3D_Models/`

| Item | File Name | Quantity | Material | Notes |
|------|-----------|----------|----------|-------|
| Chemostat Chamber Box | Multi channel chemostat v14 box.stl | 1 | PLA/PETG | Main enclosure |
| Temperature Module Box | Multi channel chemostat v5 TEMP.stl | 1 | PLA/PETG | Optional |
| Plant Maze Base | plant maze.stl | 1 | PLA | For aggregation studies |
| Plant Maze Lid | plant maze lid.stl | 1 | PLA | Covers maze |

**Print Settings:**
- Layer height: 0.2mm
- Infill: 20%
- Supports: As needed
- Material: PLA or PETG recommended

## PCB Manufacturing

### Gerber Files
Located in `Hardware/PCB/`:
- All layers included (copper, mask, silkscreen, edges)
- Drill files (PTH and NPTH)
- Job file for manufacturer specifications

**Recommended PCB Specs:**
- Layers: 2
- Thickness: 1.6mm
- Copper weight: 1 oz (35 μm)
- Surface finish: HASL or ENIG
- Minimum trace width: 0.3mm
- Minimum clearance: 0.3mm

**Manufacturers:**
- JLCPCB
- PCBWay
- OSH Park
- Seeed Studio Fusion

## Sensors and Measurement (Optional)

### Temperature Sensing
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| PT100 RTD Sensor | 3-wire, Class A | 1 | Precise temperature |
| MAX31865 Module | RTD-to-digital converter | 1 | SPI interface |

### pH Measurement (Future)
| Item | Specification | Quantity | Notes |
|------|---------------|----------|-------|
| pH Probe | Waterproof, 0-14 range | 1 | Optional addition |
| pH Interface Board | Analog or digital | 1 | Signal conditioning |

## Tools Required

### For Assembly
- Soldering iron and solder
- Wire strippers/cutters
- Screwdriver set (Phillips, flathead)
- Multimeter
- Heat shrink tubing
- Hot glue gun (for strain relief)

### For Calibration
- Analytical balance (0.01g precision)
- Graduated cylinder or pipette (10ml)
- Stopwatch or timer
- Distilled water

## Media and Reagents

### For *Capsaspora owczarzaki*
| Item | Purpose | Notes |
|------|---------|-------|
| ATCC 1034 Medium | Growth medium | Or equivalent |
| Fetal Bovine Serum | 5% in medium | Heat-inactivated |
| Antibiotics | Contamination prevention | Pen/Strep optional |
| Signal Compounds | Experimental stimuli | User-defined |

## Computer Requirements

### Host Computer (for Cellpose integration)
- **OS:** macOS, Linux, or Windows
- **RAM:** 8GB minimum, 16GB recommended
- **Processor:** Multi-core, 2.4GHz+
- **GPU:** Optional but recommended for Cellpose
- **Storage:** 100GB+ for image data

### Software
- **Python 3.8+** (for host control)
- **Mosquitto MQTT broker** (for remote control)
- **Cellpose** (for cell counting)
- **Thonny IDE** (for ESP32 programming)
- **OpenCV** (for image processing)

## Cost Estimate

### Budget Breakdown (USD, approximate)
| Category | Cost Range |
|----------|------------|
| Electronics (ESP32, MOSFETs, PCB) | $50-80 |
| Peristaltic Pumps (4×) | $60-200 |
| Tubing and Connectors | $30-50 |
| 3D Printing Materials | $20-40 |
| Power Supplies | $20-30 |
| Microscope Camera (optional) | $50-200 |
| Chamber Components | $20-40 |
| **Total (Basic)** | **$250-640** |
| **Total (with Camera)** | **$300-840** |

**Note:** Costs vary by supplier, quantity, and location. Bulk purchases reduce per-unit cost.

## Suppliers

### Electronics
- **Mouser Electronics** - mouser.com
- **DigiKey** - digikey.com
- **SparkFun** - sparkfun.com
- **Adafruit** - adafruit.com
- **AliExpress** - aliexpress.com (budget option)

### Pumps and Fluidics
- **Cole-Parmer** - coleparmer.com
- **Kamoer** - kamoer.com
- **Adafruit** - adafruit.com
- **AliExpress** - aliexpress.com

### 3D Printing Services
- **Shapeways** - shapeways.com
- **Sculpteo** - sculpteo.com
- **3D Hubs** - 3dhubs.com
- Local maker spaces

### PCB Manufacturing
- **JLCPCB** - jlcpcb.com
- **PCBWay** - pcbway.com
- **OSH Park** - oshpark.com

## Assembly Time

- **PCB Assembly:** 2-3 hours
- **Pump Integration:** 1-2 hours
- **3D Printing:** 10-20 hours (automated)
- **Chamber Assembly:** 1 hour
- **Software Setup:** 2-3 hours
- **Calibration:** 2-4 hours
- **Total:** ~15-30 hours (mostly automated printing)

## Storage and Organization

### Recommended Storage
- Small parts organizer for resistors, diodes
- Labeled containers for tubing sections
- Desiccant packs for electronics
- Clean, dry environment
- Temperature-controlled for media

## Calibration Materials

| Item | Purpose | Quantity |
|------|---------|----------|
| Distilled Water | Flow rate calibration | 500ml |
| Collection Vessels | Weighing pump output | 4× 50ml |
| Reference Weights | Balance calibration | Standard set |

## Maintenance Supplies

| Item | Purpose | Replacement Frequency |
|------|---------|----------------------|
| Pump Tubing | Prevent wear | Every 3-6 months |
| Silicone Grease | Seal maintenance | As needed |
| Isopropanol | Cleaning | As needed |
| Bleach Solution | Sterilization | As needed |
| Spare MOSFETs | Component failure | Keep 2-3 on hand |

## Quality Control Checklist

Before first use, verify:
- [ ] All solder joints secure and clean
- [ ] No shorts between power rails
- [ ] ESP32 boots and connects to WiFi
- [ ] All 4 pumps respond to PWM commands
- [ ] LED brightness adjustable
- [ ] Status LED indicates system state
- [ ] No leaks in fluidic connections
- [ ] Chamber maintains constant volume
- [ ] Temperature sensor (if used) reads accurately
- [ ] Data logging creates valid files
- [ ] Emergency stop functions correctly

## Safety Equipment

### Personal Protective Equipment
- Safety glasses
- Lab coat
- Nitrile gloves
- Closed-toe shoes

### Lab Safety
- Fire extinguisher nearby
- First aid kit
- Spill cleanup materials
- Biohazard disposal (if needed)
- Emergency contact numbers posted

## Documentation

Keep records of:
- Component serial numbers
- Calibration dates and values
- Maintenance log
- Experiment parameters
- Any modifications to design

## Support

For questions or issues:
- Check `MCMC_Software_Spec.md` for technical details
- Review `README.md` for troubleshooting
- Contact: [Your contact information]

---

**Last Updated:** September 2025  
**Version:** 1.0  
**Platform:** Microscope Mounted Chemostat (MCMC)
