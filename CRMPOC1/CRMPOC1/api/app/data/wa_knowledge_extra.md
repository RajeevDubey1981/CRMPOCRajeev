# Extra knowledge (built from the files in the Sarvam knowledge bases)

Source files: AC_Fault_Code_Reference_Unit.docx, INDcool_AC_Model_Directory.docx, INDcool_Full_Product_Directory.docx and the
split AC user manual. Built by scripts/build_wa_knowledge_extra.py. The rate card documents are intentionally not included.

## How to handle error codes and AC problems on WhatsApp

- Explain what the code or problem means in simple words. Suggest ONLY safe customer steps: switch the AC off at the main
  power, wait 3 minutes, switch on again; clean the air filter; replace the remote controller batteries; keep doors and windows closed.
- Never tell a customer to open the indoor or outdoor unit, touch the wiring or circuit board, measure resistance, or handle
  refrigerant. Technical checks in the explanations below are for the service technician only.
- If the problem is still there after the safe steps, offer to register a service request. Ask for the model, the error code and
  the PIN code. Warranty is decided by the service team, so do not promise a free repair.
- For smoke, a burning smell or sparks, tell the customer to switch the AC off at the main power and hand over to staff.
- Where this extra knowledge and the product pages in the main knowledge differ, prefer the main product pages (newer) and
  offer to confirm with sales.

## Product catalogue


## Split AC error codes


### Split AC error code EE: Indoor unit EEPROM fault

- Error code shown on the indoor unit display: EE (outdoor unit light flashes: 25)
- Unit: IDU
- Meaning: Indoor unit EEPROM fault
- Details for the technician: The indoor unit's memory chip (which stores its configuration/calibration data) can't be read or has become corrupted. Usually caused by a power surge, static discharge, or a failing memory IC. First step: power-cycle the unit. If EE returns, the indoor control board's memory needs reflashing or the board needs replacing.

### Split AC error code E1: Indoor fan fault

- Error code shown on the indoor unit display: E1 (outdoor unit light flashes: 26)
- Unit: IDU
- Meaning: Indoor fan fault
- Details for the technician: The indoor blower motor isn't reaching or reporting its expected speed. Check for a physically blocked or jammed blower wheel, a worn/seized fan motor, a failed run capacitor (on non-DC motors), or a damaged feedback wire between the motor and the control board.

### Split AC error code E2: Indoor fan zero-crossing detection abnormal

- Error code shown on the indoor unit display: E2 (outdoor unit light flashes: 27)
- Unit: IDU
- Meaning: Indoor fan zero-crossing detection abnormal
- Details for the technician: The control board can't detect the timing (zero-crossing) signal from the indoor fan motor, which it needs to control fan speed. This points to a fault in the motor's driver/feedback circuit or a bad connector between the motor and the board, rather than the motor being physically stuck.

### Split AC error code E3: Indoor coil & sensor fault

- Error code shown on the indoor unit display: E3 (outdoor unit light flashes: 28)
- Unit: IDU
- Meaning: Indoor coil & sensor fault
- Details for the technician: The temperature sensor on the indoor coil is giving a reading outside the possible range (open-circuit or short-circuit) — meaning the sensor or its wiring has failed. Test the sensor's resistance against the spec value at room temperature and check the wire for damage or corrosion.

### Split AC error code E4: Indoor ambient temperature sensor fault

- Error code shown on the indoor unit display: E4 (outdoor unit light flashes: 29)
- Unit: IDU
- Meaning: Indoor ambient temperature sensor fault
- Details for the technician: Same failure mode as E3, but for the sensor that reads room air temperature rather than coil temperature. Check sensor resistance and wiring continuity.

### Split AC error code E0: Outdoor unit EEPROM fault

- Error code shown on the indoor unit display: E0 (outdoor unit light flashes: 1)
- Unit: ODU
- Meaning: Outdoor unit EEPROM fault
- Details for the technician: The outdoor control board's memory chip can't be read or is corrupted — the outdoor-side equivalent of EE. Power-cycle first; a fault that persists means the outdoor board needs reflashing or replacement.

### Split AC error code E6: Indoor-outdoor communication fault

- Error code shown on the indoor unit display: E6 (outdoor unit light flashes: 2)
- Unit: IDU + ODU
- Meaning: Indoor-outdoor communication fault
- Details for the technician: The indoor and outdoor units have lost the signal connection between them over the wire that links their terminal blocks. This is one of the most common inverter AC faults overall. Check first: a loose, damaged, or corroded interconnecting wire, incorrect wire gauge or an overly long run, or moisture at the terminals. Only if the wiring tests fine should you suspect the transmit/receive circuitry on either board.

### Split AC error code E8: Outdoor communication fault

- Error code shown on the indoor unit display: E8 (outdoor unit light flashes: — (steady))
- Unit: ODU
- Meaning: Outdoor communication fault
- Details for the technician: A variant communication failure reported specifically from the outdoor side's signalling logic — shown as a continuous/irregular indicator rather than a fixed flash count. Troubleshoot the same way as E6: check the interconnecting wire first.

### Split AC error code F1: Compressor starting abnormal (phase failure / reverse)

- Error code shown on the indoor unit display: F1 (outdoor unit light flashes: 4)
- Unit: ODU
- Meaning: Compressor starting abnormal (phase failure / reverse)
- Details for the technician: The compressor is failing to start correctly — either a missing electrical phase (on 3-phase units) or wrong rotation direction has been detected. Check compressor winding resistance across U-V-W, verify phase sequence and wiring, and confirm the compressor itself isn't seized.

### Split AC error code F2: Compressor out-of-step fault

- Error code shown on the indoor unit display: F2 (outdoor unit light flashes: 5)
- Unit: ODU
- Meaning: Compressor out-of-step fault
- Details for the technician: The compressor motor loses electrical synchronisation mid-run. Common causes: low refrigerant charge putting abnormal load on the compressor, a mechanical jam inside the compressor, unstable incoming voltage, or a degraded IPM drive module.

### Split AC error code F3: IPM module fault

- Error code shown on the indoor unit display: F3 (outdoor unit light flashes: 6)
- Unit: ODU
- Meaning: IPM module fault
- Details for the technician: The Intelligent Power Module — the power-transistor block that drives the compressor — has tripped its own internal protection (overcurrent, overheat, or short-circuit). Check compressor insulation resistance to ground, inspect the IPM's heatsink mounting/thermal paste, and test the module's output. Often needs outdoor board/IPM replacement.

### Split AC error code F4: Compressor shell/roof fault or protection

- Error code shown on the indoor unit display: F4 (outdoor unit light flashes: 7)
- Unit: ODU
- Meaning: Compressor shell/roof fault or protection
- Details for the technician: A temperature protection on the compressor's outer shell/discharge area has tripped, usually from overheating due to low refrigerant, poor outdoor airflow, or excessive load. Check refrigerant level and outdoor coil for blockage.

### Split AC error code F5: Discharge temperature sensor fault

- Error code shown on the indoor unit display: F5 (outdoor unit light flashes: 8)
- Unit: ODU
- Meaning: Discharge temperature sensor fault
- Details for the technician: The sensor monitoring the compressor's discharge (hot, outlet) gas temperature is open- or short-circuit. Check resistance against spec and inspect wiring; replace the sensor if faulty.

### Split AC error code F6: Suction temperature sensor fault

- Error code shown on the indoor unit display: F6 (outdoor unit light flashes: 9)
- Unit: ODU
- Meaning: Suction temperature sensor fault
- Details for the technician: Same failure mode as F5, but for the sensor on the suction (return gas) line. Check resistance and wiring.

### Split AC error code F7: Outdoor coil temperature sensor fault

- Error code shown on the indoor unit display: F7 (outdoor unit light flashes: 10)
- Unit: ODU
- Meaning: Outdoor coil temperature sensor fault
- Details for the technician: The sensor used for defrost control and coil protection on the outdoor coil has failed. Check sensor and wiring.

### Split AC error code F8: Outdoor ambient temperature sensor fault

- Error code shown on the indoor unit display: F8 (outdoor unit light flashes: 11)
- Unit: ODU
- Meaning: Outdoor ambient temperature sensor fault
- Details for the technician: The sensor reading outside air temperature at the outdoor unit has failed. Check sensor and wiring.

### Split AC error code F9: Outdoor DC fan fault

- Error code shown on the indoor unit display: F9 (outdoor unit light flashes: 12)
- Unit: ODU
- Meaning: Outdoor DC fan fault
- Details for the technician: The outdoor (condenser) fan motor isn't responding correctly — no rotation feedback or abnormal speed. Check for a blocked/obstructed fan blade, test the motor directly, and inspect the fan's driver circuit on the board.

### Split AC error code P1: Outdoor machine AC current protection

- Error code shown on the indoor unit display: P1 (outdoor unit light flashes: 13)
- Unit: ODU
- Meaning: Outdoor machine AC current protection
- Details for the technician: The total AC input current drawn by the outdoor unit has exceeded the safe threshold. Measure actual running current against the nameplate rating and check for another fault (like a failing compressor) causing the excess draw.

### Split AC error code P2: Compressor phase current protection

- Error code shown on the indoor unit display: P2 (outdoor unit light flashes: 14)
- Unit: ODU
- Meaning: Compressor phase current protection
- Details for the technician: Current on one or more compressor motor phases has exceeded the protection limit, which exists to protect the windings from overcurrent damage. Check system pressures for a restriction/overcharge and verify actual compressor current draw.

### Split AC error code P3: Outdoor unit high/low AC voltage protection

- Error code shown on the indoor unit display: P3 (outdoor unit light flashes: 15)
- Unit: ODU
- Meaning: Outdoor unit high/low AC voltage protection
- Details for the technician: Incoming mains supply voltage to the outdoor unit is outside the acceptable operating range. Measure actual supply voltage under load — this is very often an unstable mains supply or undersized/long wiring causing voltage drop, not a unit fault. A voltage stabiliser may be needed.

### Split AC error code P4: DC voltage high/low protection

- Error code shown on the indoor unit display: P4 (outdoor unit light flashes: 16)
- Unit: ODU
- Meaning: DC voltage high/low protection
- Details for the technician: The internal DC bus voltage (the stage after AC-to-DC rectification that feeds the compressor drive) is out of range. Largely a board-level fault — check input voltage first, then the rectifier/capacitor bank on the outdoor drive board.

### Split AC error code P5: IPM high-temperature protection

- Error code shown on the indoor unit display: P5 (outdoor unit light flashes: 17)
- Unit: ODU
- Meaning: IPM high-temperature protection
- Details for the technician: The power module's own temperature sensor has tripped a high-temperature cutout before an actual failure occurs — effectively an early warning ahead of F3. Check for poor heatsink thermal contact, a dirty/blocked outdoor coil, a failing outdoor fan, or high ambient temperature combined with heavy load.

### Split AC error code P6: Discharge temperature overheat protection

- Error code shown on the indoor unit display: P6 (outdoor unit light flashes: 18)
- Unit: ODU
- Meaning: Discharge temperature overheat protection
- Details for the technician: The compressor's discharge gas temperature has genuinely exceeded the safe limit — a real thermal event, not just a sensor fault. Check refrigerant charge and system pressures; do not simply top up gas without first confirming there's no leak or blockage.

### Split AC error code P7: Cooling — indoor coil anti-freeze protection

- Error code shown on the indoor unit display: P7 (outdoor unit light flashes: 19)
- Unit: IDU
- Meaning: Cooling — indoor coil anti-freeze protection
- Details for the technician: The indoor coil is at risk of icing over during cooling mode. Check the air filter (clean/replace if dirty), inspect the indoor coil for dirt buildup, and verify airflow and refrigerant charge — a restricted expansion device (capillary/EEV) can also cause this.

### Split AC error code P8: Outdoor coil overheat protection

- Error code shown on the indoor unit display: P8 (outdoor unit light flashes: 20)
- Unit: ODU
- Meaning: Outdoor coil overheat protection
- Details for the technician: The outdoor coil is running hotter than allowed, typically in heating mode. Check for a blocked outdoor coil, a failed outdoor fan, refrigerant overcharge, or airflow obstruction around the outdoor unit.

### Split AC error code P9: Heating — indoor coil overheat protection

- Error code shown on the indoor unit display: P9 (outdoor unit light flashes: 21)
- Unit: IDU
- Meaning: Heating — indoor coil overheat protection
- Details for the technician: During heating mode, the indoor coil temperature has exceeded the safe limit. Check filter and coil cleanliness and verify indoor fan speed — poor indoor airflow is the usual cause.

### Split AC error code PC: Cooling — outdoor ambient temperature too low protection

- Error code shown on the indoor unit display: PC (outdoor unit light flashes: 22)
- Unit: ODU
- Meaning: Cooling — outdoor ambient temperature too low protection
- Details for the technician: The unit has detected outdoor temperature below the safe range for cooling mode and has locked out compressor operation to protect it. Check the actual outdoor temperature against the unit's rated cooling range; if it's within range, suspect a faulty outdoor ambient sensor giving a false-low reading.

### Split AC error code PH: Heating — outdoor ambient temperature too high protection

- Error code shown on the indoor unit display: PH (outdoor unit light flashes: 23)
- Unit: ODU
- Meaning: Heating — outdoor ambient temperature too high protection
- Details for the technician: The reverse case of PC — outdoor temperature is too high for heating mode operation, or the ambient sensor is misreading. Verify actual vs. sensed outdoor temperature.

### Split AC error code L1: Drive bus high voltage protection

- Error code shown on the indoor unit display: L1 (outdoor unit light flashes: 31)
- Unit: ODU
- Meaning: Drive bus high voltage protection
- Details for the technician: The DC bus voltage feeding the inverter/compressor drive has spiked above the safe threshold. Check incoming supply voltage stability first; if that's normal, the outdoor drive board's bus circuit likely needs inspection.

### Split AC error code L2: Drive bus low voltage protection

- Error code shown on the indoor unit display: L2 (outdoor unit light flashes: 32)
- Unit: ODU
- Meaning: Drive bus low voltage protection
- Details for the technician: The DC bus voltage has dropped below the safe operating threshold. Check for low incoming supply voltage, an undersized/long wiring run causing voltage drop, or a weak rectifier/PFC circuit.

### Split AC error code L3: Drive phase current overload fault

- Error code shown on the indoor unit display: L3 (outdoor unit light flashes: 33)
- Unit: ODU
- Meaning: Drive phase current overload fault
- Details for the technician: One of the compressor drive's output phases has drawn current beyond the overload threshold for a sustained period. Check system pressures and compressor current draw — this overlaps closely with P2's causes.

### Split AC error code L4: Phase current sampling abnormal

- Error code shown on the indoor unit display: L4 (outdoor unit light flashes: 34)
- Unit: ODU
- Meaning: Phase current sampling abnormal
- Details for the technician: The drive board's current-sensing circuit itself (the shunt/CT used to monitor each output phase) is giving an implausible or inconsistent reading — a sensing/circuit fault rather than a genuine overcurrent event. This is a board-level diagnosis; the outdoor drive/IPM board typically needs testing or replacement.

## Split AC troubleshooting (user manual)


### Split AC problem: Remote controller not working, indoor unit not receiving the signal

Causes and solutions (split AC user manual):
- Remote signal interference such as static electricity or unstable voltage: switch the AC off at the main power, pull out the plug, wait 3 minutes, plug in and switch on.
- Remote out of range or not pointing at the receiver: the range is 8 m, point it at the receiver.
- Obstacles in between: clear the path.
- Low remote sensitivity, weak or no display: check the remote batteries and change them if needed.
- No display on the remote screen: if the remote is damaged, replace it.
- Fluorescent lamp in the room: bring the remote closer to the indoor unit or switch the fluorescent lamp off.

### Split AC problem: No air from the indoor unit

Causes and solutions (split AC user manual):
- Air inlet or outlet blocked: clear the inlet and outlet and clean the filters.
- In heating mode the indoor temperature reached the set temperature: the blower switches off, so no air comes out. This is normal.
- Heating mode was just turned on: the indoor unit starts after a delay of several minutes so it does not blow cold air. This is normal.

### Split AC problem: AC unit is not starting

Causes and solutions (split AC user manual):
- Power failure: check whether there is a power failure at your place.
- Plug not inserted properly: switch off at the main power, insert the plug properly and start again.
- Circuit breaker tripped or fuse burnt: ask a professional electrician to replace it.
- Wiring malfunction: ask a professional electrician to replace or repair the wiring.
- Unit restarting immediately after stopping: wait 3 minutes, then switch on again.
- Incorrect function setting on the remote: reset the function.

### Split AC problem: Mist blown out of the indoor unit

Cause: indoor temperature and humidity are high. Solution: the room air is cooled quickly, so after a while the temperature and humidity drop and the mist disappears. This is normal (split AC user manual).

### Split AC problem: Not able to adjust the set temperature

Causes and solutions (split AC user manual):
- The unit is in Auto mode: the temperature cannot be adjusted in Auto mode; switch to another operation mode to set the temperature.
- The required temperature is outside the range: the set temperature range is 16 to 30 degrees C.

### Split AC problem: Cooling or heating effect is not good

Causes and solutions (split AC user manual):
- Too low voltage: wait for the voltage to become normal, then operate the unit.
- Dirty filter: clean the filter.
- Set temperature not in the proper range: adjust it.
- Leaks in the room: close all doors and windows.

### Split AC problem: Odour coming from the indoor unit

Cause: an odour source nearby such as cigarette smoke. Solution: remove the odour source and clean the filter (split AC user manual).

### Split AC problem: Abnormal behaviour of the AC unit

Cause: interference such as thunder or wireless devices. Solution: switch off the power, remove the plug, wait 3 minutes, insert the plug and switch the AC on again (split AC user manual).

### Split AC problem: Vapour from the outdoor unit

Cause: heating mode is on. During defrosting in heating mode the AC may produce vapour; this is a normal phenomenon (split AC user manual).

### Split AC problem: Water flowing sound

Cause: heard when the AC is switched on or off. It is the sound of refrigerant flowing and is normal (split AC user manual). Note: the manual's own wording for this item is mixed; if the customer reports actual water leaking, offer a service request.

### Split AC problem: Cracking noise

Cause: heard when the AC is switched on or off. It is the sound of friction of plastic parts caused by expansion and contraction of panels or other parts when the temperature changes. It is normal (split AC user manual).

## AC model guide by room (older compilation, 20 Aug 2026)


### AC model directory: model, series, tonnage, stars, type and best-for rooms (part 1 of 2)

Model Number | Series | Ton | Star | Type | Compressor / Refrigerant | Key Specs | Best For
IDCACSG13K5 | Green | 1 | 5★ | Cooling | Variable Speed Inverter / Eco-Friendly | Copper condenser | Bedrooms, study rooms, small offices, cabins
IDCACSBF10K3 | Standard Inverter | 1 | 3★ | Cooling | Variable Speed Inverter / Eco-Friendly | Copper condenser, Anti-Bacterial | Small bedrooms, study rooms, small offices, apartments
IDCACSBF10K5 | Green | 1 | 5★ | Cooling | Variable Speed Inverter / Eco-Friendly | AI Convertible 6-in-1, VOC Filter | Bedrooms, study rooms, apartments, small offices
IDCACSBF13K3CSD | CSD | 1 | 3★ | Cooling | Variable Speed Inverter / R-32 | Cooling Capacity 3.45 kW, 230V/50Hz | Bedrooms, study rooms, small offices, cabins, shops
IDCACSBF16K3 | Standard Inverter | 1.3 | 3★ | Cooling | Variable Speed Inverter / Eco-Friendly | ISEER 4.47, 4600W, 45dB, up to 55°C | Medium bedrooms, living rooms, apartments, offices
IDCACSBF16K5 | Standard Inverter | 1.3 | 5★ | Cooling | Variable Speed Inverter / Eco-Friendly | ISEER 5.65, 4580W, 45dB, up to 55°C | Medium bedrooms, living rooms, apartments, offices, shops
IDCACSBF16K5CMA | Canvas (Mintair Green) | 1.3 | 5★ | Cooling | Variable Speed Inverter / R-32 | Designer mint-green panel, ultra low noise | Premium/designer interiors, contemporary bedrooms
IDCACSBF16K5CMN | Canvas (Midnight) | 1.3 | 5★ | Cooling | Variable Speed Inverter / R-32 | Designer black panel, ultra low noise | Luxury bedrooms, dark-theme interiors, designer offices
IDCACSBF16K5CFG | Canvas (Fog) | 1.3 | 5★ | Cooling | Variable Speed Inverter / R-32 | Designer grey panel, ultra low noise | Minimalist interiors, professional spaces
IDCACSBF16K5CRB | Canvas (Redbloom) | 1.3 | 5★ | Cooling | Variable Speed Inverter / R-32 | Designer red panel, ultra low noise | Designer rooms, premium homes, bold interiors
IDCACSBF18K3CSD | CSD | 1.5 | 3★ | Cooling | Variable Speed Inverter / R-32 | Anti-Bacterial Protection | Bedrooms, living rooms, offices, cabins, shops, apartments

### AC model directory: model, series, tonnage, stars, type and best-for rooms (part 2 of 2)

Model Number | Series | Ton | Star | Type | Compressor / Refrigerant | Key Specs | Best For
IDCACSBFE18K3D | Dubai | 1.5 | 3★ | Cooling | Heavy Duty Inverter / R-32 | ISEER 4.31, 5.4kW, up to 60°C, Blue Fin anti-rust | Extreme-heat regions, top-floor rooms, govt/commercial
IDCACSD18K5 | Dubai | 1.5 | 5★ | Cooling | (Dubai platform — same 60°C range) | Higher-tier sibling of IDCACSBFE18K3D | Extreme-heat regions (same as above, 5★ tier)
IDCACS18K5HE | Greeno | 1.5 | 5★ | Cooling | Variable Speed Inverter / Eco-Friendly | ISEER 5.8, 5200W, up to 52°C, 2-Way Auto Swing | Bedrooms, living rooms, premium homes, offices
IDCACSBFE18K5 | Green | 1.5 | 5★ | Cooling | Variable Speed Inverter / Eco-Friendly | Standard Green Series platform | Homes, apartments, bedrooms, living rooms, offices, retail
IDCACSBF18K5G | Green | 1.5 | 5★ | Cooling | Variable Speed Inverter / Eco-Friendly | ISEER 5.6, Convertible + Turbo Cooling | Homes, apartments, bedrooms, living rooms, premium commercial
IDCACBF18K3EF | Heavy Duty | 1.5 | 3★ | Cooling | Variable Speed Inverter | Convertible Cooling Technology | Homes, apartments, bedrooms, living rooms, offices, shops
IDCACSBF18K5HC | Greeno (Hot & Cold) | 1.5 | 5★ | Cooling + Heating | Variable Speed Inverter, Heat Pump | Cools to 52°C / heats to -15°C, 4-Way Auto | Homes needing winter heating too, hotels, commercial cabins
IDCACSBF22K3 | Premium Inverter | 1.8 | 3★ | Cooling | Variable Speed Inverter | 4-Way Auto, large-space cooling | Large bedrooms, living rooms, offices, meeting rooms, villas
IDCACSBF22K5 | Premium Inverter | 1.8 | 5★ | Cooling | Variable Speed Inverter / R-32 | ISEER 5.63, 6312W, up to ~51°C, PM0.3 Filter | Large bedrooms, living rooms, villas, offices, meeting rooms
IDCACSBFS24K5INV | Premium Inverter / Greeno | 2 | 5★ | Cooling | Variable Speed Inverter / R-32 | 6-in-1 Convertible, Digital Inverter, Wide Air Swing | Large bedrooms, villas, offices, conference rooms, restaurants

## Product directory by category (older compilation, 20 Aug 2026)


### Product directory: models by category with capacity, star rating and key spec (part 1 of 7)

INDcool — Full Product Directory (All Categories)
How to Use This Directory
This groups every product family found live on indcool.in into one reference. Model codes, capacities, and star ratings come directly from product titles/pages.
Summary — Product Count by Category
Category | Models / Count Found
Split AC (incl. Dubai Series, Canvas Series, CSD, Green, Hot & Cold) | 28
Window AC | 7
Tower / Floor-Standing AC | 4
Cassette AC | 1
Commercial Ductable AC | 11
VRF AC (outdoor units) | 2
Refrigerators | 4 confirmed (+ Double Door category advertised, no SKU found)
Deep Freezers | 5
Water Coolers (base sizes; each in up to 3 variants) | 5
Water Dispensers | 1
Geysers | 6
Ceiling Fans | 4
Exhaust Fans | 4
Commercial Ice-Making Machines | 3
Washing Machines | 2 categories advertised (no individual SKUs published yet)
Split AC — Standard Range
Model | Capacity | Star / Type | Key Spec
IDCACSG13K5 | 1 Ton | 5★, Green | ISEER value 5-5.5, Copper condenser
IDCACSN13K5 | 1 Ton | 5★ | Standard non-green 5 star tier
IDCACSBF10K3 | 1 Ton | 3★ | Anti-Bacterial coating
IDCACSBF10K5 | 1 Ton | 5★ | AI Convertible 6-in-1, VOC Filter
IDCACSBF13K3CSD | 1 Ton | 3★, CSD | Cooling 3.45 kW — Canteen Stores Dept variant
IDCACS13K3 | 1 Ton | 3★ | Inverter split, listed on price-comparison sites
IDCACSBF16K3 | 1.3 Ton | 3★ | ISEER 4.47, 4600W, 45dB, works up to 55°C
IDCACSBF16K5 | 1.3 Ton | 5★ | ISEER 5.65, 4580W, 45dB, works up to 55°C
IDCACSBF18K3CSD | 1.5 Ton | 3★, CSD | Anti-Bacterial Protection — CSD variant
IDCACSBF18K3F | 1.49 Ton | 3★, Fixed Speed (non-inverter) | Entry-level fixed-speed option
IDCACSBF18K5HI | 1.5 Ton | 5★, Inverter | Variable-speed inverter
IDCACSBF18K5HC | 1.5 Ton | 5★, Hot & Cold | All-weather heating + cooling in one unit
IDCACSBF22K5 | 1.8 Ton | 5★ | Mid-large room coverage
IDCACSBF24K3HC | 2 Ton | 3★, Hot & Cold | Larger room heating + cooling
IDCACS24K3I | 2 Ton | 3★, Inverter | Standard inverter split

### Product directory: models by category with capacity, star rating and key spec (part 2 of 7)

IDCACS18K5HE | 1.5 Ton | 5★ (Greeno line) | ISEER 5.8, 5200W, works up to 52°C, 2-way auto swing
IDCACSN18K3 | 1.5 Ton | 3★ (2022 model) | Older-generation model, may be discontinued/legacy stock
IDCACSBFE18K5 | 1.5 Ton | 5★, Green | Standard Green Series
IDCACSBF18K5G | 1.5 Ton | 5★, Green | ISEER 5.6, Convertible + Turbo Cooling
IDCACBF18K3EF | 1.5 Ton | 3★, Heavy Duty | Convertible Cooling Technology
IDCACBF18K5EF | 1.5 Ton | 5★, Heavy Duty | 5-in-1 Convertible Cooling
IDCACSBFS24K5INV | 2 Ton | 5★, Inverter | Variable-speed, larger capacity
Split AC — Dubai Series (Extreme-Heat Engineering)
Rated to keep working at ambient temperatures up to 60°C — built for regions with extreme summer heat, dust, and unstable power. Recommend this series when a customer describes very hot conditions or repeated breakdowns in peak summer.
Model | Capacity | Star / Type | Key Spec
IDCACSBFE18K3D | 1.5 Ton | 3★ | ISEER 4.31, 5.4kW, rated to work up to 60°C ambient, Blue Fin anti-rust coil — built for extreme heat/dust regions
Split AC — Canvas Series (Designer Finishes)
Same reliable core as the standard range, with designer front-panel finishes. Recommend when a customer cares about how the unit looks in a living space.
Model | Capacity | Star / Type | Key Spec
IDCACSBF16K5CRB | 1.3 Ton | 5★, Canvas (Redbloom) | Designer red front panel, ultra-low noise
IDCACSBF16K5CFG | 1.3 Ton | 5★, Canvas (Fog) | Designer grey panel, ultra-low noise
IDCACSBF16K5CMA | 1.3 Ton | 5★, Canvas (Mintair Green) | Designer mint-green panel, ultra-low noise
IDCACSBF16K5CMN | 1.3 Ton | 5★, Canvas (Midnight) | Designer black panel, ultra-low noise
Window AC
Model | Capacity | Star / Type | Key Spec
IDCACWN18K3F | 1.5 Ton | 3★, Fixed Speed | Entry-level window unit
IDCACWBF16K3 | 1.5 Ton | 3★, Inverter | Variable-speed window AC
IDCACWBF16K5 | 1.5 Ton | 5★, Inverter | Variable-speed window AC
IDCACWBF18K3 | 1.5 Ton | 3★, Inverter | Variable-speed window AC

### Product directory: models by category with capacity, star rating and key spec (part 3 of 7)

IDCACWBF18K3F | 1.5 Ton | 3★, Fixed Speed | Fixed-speed window AC
IDCACWBF18K5 | 1.5 Ton | 5★, Inverter | Variable-speed window AC
IDCACWBF22K5 | 2 Ton | 5★, Inverter | Larger-room window AC
Tower / Floor-Standing AC
Model | Capacity | Star / Type | Key Spec
IDCACF24K3F | 2 Ton | 3★, Fixed Speed | Cooling ~7,050W, floor-standing tower design
IDCACFS24K3AIN | 2 Ton | 3★, Inverter | Cooling ~7,050W, floor-standing
IDCACFS48KF | 4 Ton | Fixed Speed | Cooling ~14,100W, large-space floor-standing unit
IDCACFS48KINV | 4 Ton | Inverter | Cooling ~13,200W, large-space floor-standing unit
Cassette AC (Ceiling-Recessed, Commercial)
Model | Capacity | Star / Type | Key Spec
IDCACC24K3AIN | 2 Ton | 3★, Inverter, Cassette (ceiling-recessed) | For false-ceiling commercial installs — shops, offices, halls
Commercial Ductable AC
For centralized/commercial installations — offices, halls, retail floors. Ranges from 1.5 Ton up to 11 Ton (Heavy Commercial tier).
Model | Capacity | Star / Type | Key Spec
IDCLCD18KF | 1.5 Ton (2.0 HP) | Fixed Speed | Ductable — for centralized/commercial installs
IDCLCD18KINV | 1.5 Ton (2.0 HP) | Inverter | Ductable, variable-speed
IDCLCD24KF | 2 Ton (2.5 HP) | Fixed Speed | Ductable
IDCLCD24KINV | 2 Ton (2.5 HP) | Inverter | Ductable, variable-speed
IDCLCD36KF | 3 Ton (4.0 HP) | Fixed Speed | Ductable
IDCLCD36KINV | 3 Ton (3.5 HP) | Inverter | Ductable, variable-speed
IDCLCD48KF | 4 Ton (5.0 HP) | Fixed Speed | Ductable
IDCLCD48KINV | 4 Ton (5.0 HP) | Inverter | Ductable, variable-speed
IDCLCD66KF | 5.5 Ton | Fixed Speed, Heavy Commercial | Large commercial ducted install
IDCLCD102KF | 8.5 Ton | Fixed Speed, Heavy Commercial | Large commercial ducted install
IDCLCD132KF | 11 Ton | Fixed Speed, Heavy Commercial | Largest ducted unit in the range
VRF AC (Variable Refrigerant Flow)
Model | Capacity | Star / Type | Key Spec

### Product directory: models by category with capacity, star rating and key spec (part 4 of 7)

VRF Home Outdoor Unit — 6 HP | 6 HP | VRF (Variable Refrigerant Flow) | Space-saving multi-unit AC — one outdoor unit connects up to 8 indoor units. Price on request.
VRF Home Outdoor Unit — 10 HP | 10 HP | VRF (Variable Refrigerant Flow) | Higher-capacity outdoor unit, replaces multiple standalone outdoor units. Price on request.
 |  |  | Note: the VRF product pages' own tonnage filter sidebar shows '4.5 HP' / '8.5 HP' facets that don't match the '6 HP' / '10 HP' product titles — a data inconsistency on INDcool's own site, flagged rather than resolved by guessing.
Refrigerators
Model | Capacity | Type | Notes
IDC50SDC1 | 50 Litres | 1★, Single Door, Direct Cool | Compact — small households, dorm/cabin use
IDC100SDC1 | 100 Litres | 1★, Single Door, Direct Cool | Small households
IDC170SDC1 | 170 Litres | 1★, Single Door, Direct Cool | Available in 4 finishes: Winora, FloraRed, AquaFlora, Linish
IDCREFSD190D3 | 190 Litres | 2★, Single Door, Direct Cool | Available in 4 finishes: Linish, Winora, Florared, AquaFlora
 |  |  | Note: INDcool's category page also lists a 'Double Door Refrigerators' category, but no individual double-door model/SKU could be found published on the site as of this research — flagged as unconfirmed rather than guessed.
Deep Freezers
Model | Capacity | Type | Notes
175SDUC | 175 Litres | 5★, Single Door | Hard-top deep freezer
200SDUC | 200 Litres | 5★, Single Door | Hard-top deep freezer
300DDUC | 300 Litres | 5★, Double Door | Hard-top deep freezer
400DDUC | 400 Litres | 5★, Double Door | Hard-top deep freezer
500DDUC | 500 Litres | 5★, Double Door | Largest in the range — hard-top deep freezer
Water Coolers (Stainless Steel, Heavy-Duty)
Each base capacity is offered in up to three variants: Cold-only, Hot & Cold, and Inbuilt-RO (some sizes also offer an "All-in-One" combined variant).
Model | Capacity | Variant | Notes
IDCWC FSS40/80 | 80 Litres | Cold-only / Hot & Cold / Inbuilt RO | Full stainless-steel body, heavy-duty

### Product directory: models by category with capacity, star rating and key spec (part 5 of 7)

IDCWC FSS60/80 | 80 Litres | Cold-only / Hot & Cold / Inbuilt RO | Full stainless-steel body, heavy-duty
IDCWC FSS60/120 | 120 Litres | Cold-only / Hot & Cold / Inbuilt RO | Full stainless-steel body, heavy-duty
IDCWC FSS80/120 | 120 Litres | Cold-only / Hot & Cold / Inbuilt RO | Full stainless-steel body, heavy-duty
IDCWC FSS150/150 | 150 Litres | Cold-only / Hot & Cold / Inbuilt RO / All-in-One | Largest capacity in the water cooler range
Water Dispensers
Model | Capacity | Variant | Notes
IDCWDBLV1 | Standard countertop/bottom-load size | Bottom Load Water Dispenser | Dispenses Hot, Cold & Normal water
Geysers (Electric Water Heaters)
Deco Series and Prime Series — mostly vertical wall-mount; one horizontal option (IDCWH25H) for space-constrained installs.
Model | Capacity | Variant | Notes
IDCWH510GV | 10 Litres | Deco Series & Prime Series, Vertical | Compact geyser for 1-2 point usage
IDCWH515GV | 15 Litres | Deco Series & Prime Series, Vertical | Small household geyser
IDCWH525GV | 25 Litres | Deco Series & Prime Series, Vertical | Mid-size household geyser
IDCWH535GV | 35 Litres | Prime Series, Vertical | Larger household/small commercial use
IDCWH550GV | 50 Litres | Prime Series, Vertical | Largest vertical geyser in the range
IDCWH25H | 25 Litres | Prime Series, Horizontal | Horizontal-mount option for space-constrained installs
Fans — Ceiling & Exhaust
Model | Size | Type | Notes
IDC CF 112 | 48-inch (1200mm) | Ceiling Fan, Copper Winding | Available in multiple finishes (e.g. Creamberg, Brown); 1★ rated variant listed
IDC CF 115 | 56-inch (1400mm) | Ceiling Fan, Copper Winding | 60W motor, larger sweep for bigger rooms
IDC CF 500 | Standard ceiling size | Ceiling Fan, BLDC (energy-saving motor) | Lower power draw than copper-winding models
IDC CF 600 | 56-inch (1400mm) | Ceiling Fan, BLDC (energy-saving motor) | Larger BLDC ceiling fan
IDC EF 12 | 300mm (12-inch) | Exhaust Fan, Heavy Duty | Kitchens, bathrooms, small commercial spaces

### Product directory: models by category with capacity, star rating and key spec (part 6 of 7)

IDC EF 15 | 380mm (15-inch) | Exhaust Fan, Heavy Duty | Mid-size rooms, commercial kitchens
IDC EF 18 | 450mm | Exhaust Fan, Heavy Duty | Larger commercial/industrial spaces
IDC EF 24 | 600mm | Exhaust Fan, Heavy Duty | Largest exhaust fan in the range — industrial/warehouse use
Commercial Ice-Making Machines (Frozen Series)
Three models by size tier. INDcool publishes a dedicated "Commercial Ice Maker Catalogue (Aug 2026)" PDF on their e-catalogues page — pull exact daily-output/power specs from that document before quoting a commercial customer, since the individual product pages for these models were not resolving publicly at the time of this research.
Model | Capacity | Type | Notes
IDCIMM-60 | Unconfirmed — likely ~60 kg/day based on naming pattern | Commercial Ice-Making Machine | Smallest of 3 models. Exact daily output, dimensions, and power draw were NOT confirmed from a public source — verify against INDcool's own August 2026 Ice Making Machine catalogue PDF before quoting to a customer.
IDCIMM-130 | Unconfirmed — likely ~130 kg/day based on naming pattern | Commercial Ice-Making Machine | Mid-size model. Same caveat — confirm exact spec before quoting.
IDCIMM-210 | Unconfirmed — likely ~210 kg/day based on naming pattern | Commercial Ice-Making Machine | Largest model. Same caveat — confirm exact spec before quoting.
Washing Machines
Listed as a product category (Top Load and Front Load) with an advertised capacity range, but individual model numbers were not found published on the site — flag to a customer as "let me get the exact model list for you" rather than inventing a SKU.
Model | Capacity | Type | Notes
Not yet published with individual model/SKU | 6.5 / 7.0 / 7.5 / 8.0 kg (advertised range) | Top Load, Fully Automatic | INDcool's site currently shows this as a category description only — no specific model numbers, star ratings, or per-model specs were found published as of this research.

### Product directory: models by category with capacity, star rating and key spec (part 7 of 7)

Not yet published with individual model/SKU | Not specified | Front Load, Fully Automatic | Same as above — category exists on the site, individual SKUs not yet published/found.
Data Quality Notes
A few gaps and inconsistencies came up during this research — worth knowing about before this feeds a customer-facing agent:
Washing machines: category pages exist, but no individual SKUs, star ratings, or per-model specs are currently published on indcool.in. Advertised capacity range is 6.5–8.0 kg.
Ice-making machines: model names (IDCIMM-60/130/210) were found, but their individual product pages were not resolving publicly, and exact daily-output/power specs could not be confirmed from the website — INDcool's own August 2026 PDF catalogue is the authoritative source to pull these from.
Double-door refrigerators: advertised as a category on the site, but no specific double-door model/SKU could be found published — only single-door models (50L/100L/170L/190L) were confirmed.
VRF AC: the product titles say "6 HP" and "10 HP", but the same page's own filter sidebar lists "4.5 HP" / "8.5 HP" as tonnage facets — an inconsistency in INDcool's own site data, not resolved here by guessing.
Colour/finish variants (e.g. refrigerators in 4 finishes, geysers in 2 series) are grouped under one model line rather than counted as separate SKUs — if the voice agent needs to quote an exact live SKU/price, it should still confirm on indcool.in or the internal system rather than read a number from this document, since prices change and weren't the focus of this compile.
