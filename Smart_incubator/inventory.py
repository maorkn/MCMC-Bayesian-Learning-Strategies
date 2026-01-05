"""
Inventory and shopping-list helper for the Smart Incubator.

This module:
- Parses the Markdown BOM in Docs/parts_list.md
- Parses the KiCad schematic in Hardware/PCB/Smart incubator 2 .kicad_sch
- Aggregates items into a per-unit inventory
- Computes a shopping list for any number of units

You can run it directly, e.g.:
    python inventory.py --units 5
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent
PARTS_MD_PATH = ROOT / "Docs" / "parts_list.md"
KICAD_SCH_PATH = ROOT / "Hardware" / "PCB" / "Smart incubator 2 .kicad_sch"


# Simplified teardown BOM for the "no TEC1" incubator variant.
# Quantities are per incubator unit.
TEARDOWN_BOM_NO_TEC1 = [
    # Main assembly (non-PCB)
    {
        "group": "assembly",
        "name": "PTC heater",
        "spec": "PTC 12V 120C",
        "qty_per_unit": 2,
    },
    {
        "group": "assembly",
        "name": "Thermal cutoff",
        "spec": "KSD 9700 250V 5A 65C",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "Vibration motor",
        "spec": "V919",
        "qty_per_unit": 2,
    },
    {
        "group": "assembly",
        "name": "RTD interface",
        "spec": "MAX31865 PT100 Adafruit board",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "SD card SPI module",
        "spec": "MicroSD SPI breakout",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "SD card",
        "spec": "MicroSD card",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "OLED display",
        "spec": "0.96\" OLED 41215",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "Cooling fan (external)",
        "spec": "12V 40 mm",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "Mixing fan (internal)",
        "spec": "30 mm 12V",
        "qty_per_unit": 1,
    },
    {
        "group": "assembly",
        "name": "Lid PCB LED array",
        "spec": "Lid PCB + 6 white LEDs + 6×430Ω resistors",
        "qty_per_unit": 1,
    },
    # Control PCB components
    {
        "group": "pcb",
        "name": "Header for MAX31865 board",
        "spec": "8-pin straight header",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "Header for SD card module",
        "spec": "6-pin straight header",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "Header for OLED",
        "spec": "4-pin straight header",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "Header for ESP32",
        "spec": "2×18-pin header set",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "SMD resistors 220Ω",
        "spec": "SMB 220Ω",
        "qty_per_unit": 3,
    },
    {
        "group": "pcb",
        "name": "SMD LED (red)",
        "spec": "Red SMB LED",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "SMD LED (green)",
        "spec": "Green SMB LED",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "SMD LED (yellow)",
        "spec": "Yellow SMB LED",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "Resistors 10kΩ",
        "spec": "Through-hole or SMD 10kΩ",
        "qty_per_unit": 3,
    },
    {
        "group": "pcb",
        "name": "Resistors 220Ω",
        "spec": "Through-hole or SMD 220Ω",
        "qty_per_unit": 3,
    },
    {
        "group": "pcb",
        "name": "2-pin cable jacks",
        "spec": "Screw or JST, 2-pin",
        "qty_per_unit": 5,
    },
    {
        "group": "pcb",
        "name": "3-pin cable jack",
        "spec": "Screw or JST, 3-pin",
        "qty_per_unit": 1,
    },
    {
        "group": "pcb",
        "name": "MOSFETs",
        "spec": "Power MOSFET (e.g., IRFZ44N)",
        "qty_per_unit": 3,
    },
    {
        "group": "pcb",
        "name": "Resettable fuse",
        "spec": "F1 10A PPTC",
        "qty_per_unit": 1,
    },
]


@dataclass
class Part:
    """Single BOM entry from the Markdown parts list."""

    source: str  # "docs"
    component: str
    specification: str
    quantity_raw: str
    approx_cost: str
    notes: str
    section: str
    subsection: str
    optional: bool
    tool: bool

    @property
    def quantity_numeric(self) -> Optional[float]:
        """
        Extract the first numeric value from the quantity string, if present.
        Examples:
            "1" -> 1
            "1-2" -> 1
            "40+" -> 40
            "1m" -> 1
            "1 set" -> 1
        """
        match = re.match(r"\s*(\d+(\.\d+)?)", self.quantity_raw)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None


@dataclass
class PCBItem:
    """Single component type from the KiCad schematic BOM."""

    source: str  # "pcb"
    lib_id: str
    value: str
    count: int


def parse_parts_list_markdown(path: Path = PARTS_MD_PATH) -> List[Part]:
    """
    Parse Docs/parts_list.md into a list of Part objects.

    The parser is deliberately simple and robust, not a full Markdown parser.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Parts list Markdown not found at {path}")

    parts: List[Part] = []
    current_section = ""
    current_subsection = ""
    in_table = False
    table_header_seen = False

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            # Section / subsection headings
            if stripped.startswith("## "):
                # e.g. "## 1. Control & Processing"
                current_section = stripped.lstrip("#").strip()
                current_subsection = ""
                in_table = False
                table_header_seen = False
                continue

            if stripped.startswith("### "):
                current_subsection = stripped.lstrip("#").strip()
                in_table = False
                table_header_seen = False
                continue

            # Detect table header for component tables
            if stripped.startswith("| Component |") and "Approx. Cost" in stripped:
                in_table = True
                table_header_seen = True
                continue

            # Ignore the markdown header separator row
            if in_table and table_header_seen and stripped.startswith("|---"):
                # We have seen the header and separator; next lines are data rows
                continue

            # End of table on blank line or subtotal line
            if in_table and (stripped == "" or stripped.startswith("**Subtotal")):
                in_table = False
                table_header_seen = False
                continue

            # Parse table rows
            if in_table and stripped.startswith("|") and stripped.endswith("|"):
                # Split row into cells, stripping outer pipes
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) < 5:
                    continue
                component, specification, quantity, approx_cost, notes = cells[:5]

                section_lower = current_section.lower()
                optional = "optional" in section_lower
                tool = "tool" in section_lower

                parts.append(
                    Part(
                        source="docs",
                        component=component,
                        specification=specification,
                        quantity_raw=quantity,
                        approx_cost=approx_cost,
                        notes=notes,
                        section=current_section,
                        subsection=current_subsection,
                        optional=optional,
                        tool=tool,
                    )
                )

    return parts


def _parse_kicad_symbols(lines: List[str]) -> Iterable[Dict[str, str]]:
    """
    Very lightweight parser for KiCad .kicad_sch symbol blocks.

    Yields dicts with keys like "lib_id", "Reference", "Value", "in_bom", "dnp".
    """
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip()
        if not stripped.startswith("(symbol"):
            i += 1
            continue

        # Track parentheses depth for this symbol block
        depth = line.count("(") - line.count(")")
        symbol_data: Dict[str, str] = {}

        i += 1
        while i < n and depth > 0:
            l = lines[i]
            depth += l.count("(") - l.count(")")
            s = l.strip()

            # lib_id
            if s.startswith("(lib_id "):
                m = re.search(r'\(lib_id\s+"([^"]+)"', s)
                if m:
                    symbol_data["lib_id"] = m.group(1)

            # in_bom / dnp flags
            elif s.startswith("(in_bom "):
                symbol_data["in_bom"] = "yes" if "yes" in s else "no"
            elif s.startswith("(dnp "):
                symbol_data["dnp"] = "yes" if "yes" in s else "no"

            # property lines, e.g. (property "Reference" "R1"
            elif s.startswith("(property "):
                m = re.search(r'\(property\s+"([^"]+)"\s+"([^"]*)"', s)
                if m:
                    key, value = m.group(1), m.group(2)
                    symbol_data[key] = value

            i += 1

        if "lib_id" in symbol_data and "Reference" in symbol_data:
            # Only yield true schematic instances, not library symbol templates
            # Library symbols at the top of the file do not have a lib_id entry.
            yield symbol_data


def parse_kicad_schematic_bom(path: Path = KICAD_SCH_PATH) -> List[PCBItem]:
    """
    Parse the KiCad schematic and aggregate components into a PCB BOM.
    """
    if not path.is_file():
        raise FileNotFoundError(f"KiCad schematic not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    symbol_dicts = list(_parse_kicad_symbols(lines))

    # Aggregate by (lib_id, Value)
    counts: Dict[Tuple[str, str], int] = {}
    for sym in symbol_dicts:
        if sym.get("in_bom", "yes") == "no":
            continue
        if sym.get("dnp", "no") == "yes":
            continue

        lib_id = sym.get("lib_id", "").strip()
        value = sym.get("Value", "").strip() or sym.get("Description", "").strip()
        if not lib_id:
            continue

        key = (lib_id, value)
        counts[key] = counts.get(key, 0) + 1

    items: List[PCBItem] = []
    for (lib_id, value), count in sorted(counts.items(), key=lambda kv: kv[0]):
        items.append(PCBItem(source="pcb", lib_id=lib_id, value=value, count=count))

    return items


def build_inventory(
    include_optional: bool = False,
    include_tools: bool = False,
) -> Dict[str, List[Dict[str, object]]]:
    """
    Build a combined inventory view from Markdown BOM and PCB schematic.

    Returns a dict with two top-level keys:
        "parts": list of dicts (Docs-based BOM entries)
        "pcb": list of dicts (aggregated PCB components)
    """
    parts = parse_parts_list_markdown()
    pcb_items = parse_kicad_schematic_bom()

    filtered_parts: List[Part] = []
    for p in parts:
        if not include_optional and p.optional:
            continue
        if not include_tools and p.tool:
            continue
        filtered_parts.append(p)

    return {
        "parts": [asdict(p) for p in filtered_parts],
        "pcb": [asdict(item) for item in pcb_items],
    }


def compute_shopping_list(
    units: int,
    include_optional: bool = False,
    include_tools: bool = False,
) -> Dict[str, List[Dict[str, object]]]:
    """
    Compute a shopping list for the requested number of incubator units.

    For Markdown-based parts, a per-unit numeric quantity is inferred when
    possible; otherwise the quantity is left as a textual expression.

    For PCB components, counts are always per board; they are multiplied by
    the number of units.
    """
    inv = build_inventory(include_optional=include_optional, include_tools=include_tools)

    shopping_parts: List[Dict[str, object]] = []
    for p_dict in inv["parts"]:
        p = Part(**p_dict)  # type: ignore[arg-type]
        q_num = p.quantity_numeric
        total_numeric: Optional[float] = q_num * units if q_num is not None else None

        if total_numeric is not None and total_numeric.is_integer():
            total_numeric = int(total_numeric)

        shopping_parts.append(
            {
                "source": p.source,
                "component": p.component,
                "specification": p.specification,
                "quantity_per_unit_raw": p.quantity_raw,
                "quantity_per_unit_numeric": q_num,
                "total_quantity_numeric": total_numeric,
                "units": units,
                "approx_cost": p.approx_cost,
                "notes": p.notes,
                "section": p.section,
                "subsection": p.subsection,
                "optional": p.optional,
                "tool": p.tool,
            }
        )

    shopping_pcb: List[Dict[str, object]] = []
    for item_dict in inv["pcb"]:
        pcb = PCBItem(**item_dict)  # type: ignore[arg-type]
        total = pcb.count * units
        shopping_pcb.append(
            {
                "source": pcb.source,
                "lib_id": pcb.lib_id,
                "value": pcb.value,
                "count_per_unit": pcb.count,
                "total_count": total,
                "units": units,
            }
        )

    return {"parts": shopping_parts, "pcb": shopping_pcb}


def interactive_inventory_setup(
    output_path: Path,
    include_optional: bool = False,
    include_tools: bool = False,
) -> None:
    """
    Simple CLI wizard to capture inventory numbers for each item.

    Goes line by line over the combined inventory and asks you to enter:
      - a number  -> how many you currently have
      - 'NA'      -> you do not use/need this item
      - blank     -> skip for now

    The result is written as a JSON file that you can manually edit later.
    """
    inv = build_inventory(include_optional=include_optional, include_tools=include_tools)

    print("\n=== Interactive Inventory Setup ===\n")
    print("For each item, enter:")
    print("  - a number  -> current stock on hand")
    print("  - 'NA'      -> you never use this item")
    print("  - blank     -> skip / fill in later")
    print(f"\nInventory JSON will be saved to: {output_path}\n")

    items: List[Dict[str, object]] = []

    # High-level parts from Docs/parts_list.md
    print("--- Parts from Docs/parts_list.md ---")
    for idx, p_dict in enumerate(inv["parts"], 1):
        p = Part(**p_dict)  # type: ignore[arg-type]
        print("\n------------------------------------------------------------")
        print(f"[{idx}] {p.component}")
        print(f"    Spec      : {p.specification}")
        print(f"    Section   : {p.section}")
        if p.subsection:
            print(f"    Subsection: {p.subsection}")
        q_num = p.quantity_numeric
        if q_num is not None:
            print(f"    Per-unit requirement (parsed): {q_num}")

        while True:
            resp = input("Inventory on hand (number / NA / blank): ").strip()
            if resp == "":
                inventory_raw = ""
                inventory_numeric: Optional[float] = None
                break
            if resp.upper() == "NA":
                inventory_raw = "NA"
                inventory_numeric = None
                break
            try:
                num = float(resp)
                inventory_raw = resp
                if num.is_integer():
                    inventory_numeric = int(num)
                else:
                    inventory_numeric = num
                break
            except ValueError:
                print("  Please enter a number, 'NA', or press Enter to skip.")

        items.append(
            {
                "kind": "docs_part",
                "component": p.component,
                "specification": p.specification,
                "section": p.section,
                "subsection": p.subsection,
                "optional": p.optional,
                "tool": p.tool,
                "quantity_per_unit_raw": p.quantity_raw,
                "quantity_per_unit_numeric": q_num,
                "inventory_raw": inventory_raw,
                "inventory_numeric": inventory_numeric,
            }
        )

    # PCB components from KiCad schematic
    print("\n--- PCB components from KiCad schematic ---")
    for idx, item_dict in enumerate(inv["pcb"], 1):
        pcb = PCBItem(**item_dict)  # type: ignore[arg-type]
        print("\n------------------------------------------------------------")
        print(f"[PCB {idx}] {pcb.lib_id}")
        print(f"    Value            : {pcb.value}")
        print(f"    Per-board count  : {pcb.count}")

        while True:
            resp = input("Inventory on hand (number / NA / blank): ").strip()
            if resp == "":
                inventory_raw = ""
                inventory_numeric: Optional[float] = None
                break
            if resp.upper() == "NA":
                inventory_raw = "NA"
                inventory_numeric = None
                break
            try:
                num = float(resp)
                inventory_raw = resp
                if num.is_integer():
                    inventory_numeric = int(num)
                else:
                    inventory_numeric = num
                break
            except ValueError:
                print("  Please enter a number, 'NA', or press Enter to skip.")

        items.append(
            {
                "kind": "pcb_component",
                "lib_id": pcb.lib_id,
                "value": pcb.value,
                "count_per_board": pcb.count,
                "inventory_raw": inventory_raw,
                "inventory_numeric": inventory_numeric,
            }
        )

    payload: Dict[str, object] = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "include_optional": include_optional,
        "include_tools": include_tools,
        "items": items,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nSaved inventory data to: {output_path}\n")


def interactive_teardown_inventory_setup(
    output_path: Path,
) -> None:
    """
    Interactive inventory entry for the simplified teardown BOM (no TEC1).

    Goes item by item over TEARDOWN_BOM_NO_TEC1 and asks for:
      - a number  -> how many you currently have
      - 'NA'      -> you do not use/need this item
      - blank     -> skip for now

    Saves a compact JSON file you can edit later.
    """
    print("\n=== Interactive Inventory Setup (Teardown BOM: no TEC1) ===\n")
    print("For each item, enter:")
    print("  - a number  -> current stock on hand")
    print("  - 'NA'      -> you never use this item")
    print("  - blank     -> skip / fill in later")
    print(f"\nInventory JSON will be saved to: {output_path}\n")

    items: List[Dict[str, object]] = []

    for idx, item in enumerate(TEARDOWN_BOM_NO_TEC1, 1):
        name = item["name"]
        spec = item.get("spec", "")
        group = item.get("group", "")
        qty_per_unit = item.get("qty_per_unit", 1)

        print("\n------------------------------------------------------------")
        print(f"[{idx}] {name}")
        if spec:
            print(f"    Spec          : {spec}")
        if group:
            print(f"    Group         : {group}")
        print(f"    Per-unit qty  : {qty_per_unit}")

        while True:
            resp = input("Inventory on hand (number / NA / blank): ").strip()
            if resp == "":
                inventory_raw = ""
                inventory_numeric: Optional[float] = None
                break
            if resp.upper() == "NA":
                inventory_raw = "NA"
                inventory_numeric = None
                break
            try:
                num = float(resp)
                inventory_raw = resp
                if num.is_integer():
                    inventory_numeric = int(num)
                else:
                    inventory_numeric = num
                break
            except ValueError:
                print("  Please enter a number, 'NA', or press Enter to skip.")

        items.append(
            {
                "group": group,
                "name": name,
                "spec": spec,
                "qty_per_unit": qty_per_unit,
                "inventory_raw": inventory_raw,
                "inventory_numeric": inventory_numeric,
            }
        )

    payload: Dict[str, object] = {
        "variant": "no_TEC1_teardown",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "items": items,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nSaved teardown inventory data to: {output_path}\n")


def _print_table(rows: List[Dict[str, object]], fields: List[str]) -> None:
    """Pretty-print a simple text table to stdout."""
    if not rows:
        print("(no entries)")
        return

    # Compute column widths
    col_widths: Dict[str, int] = {}
    for field in fields:
        max_len = max(len(str(r.get(field, ""))) for r in rows)
        col_widths[field] = max(max_len, len(field))

    # Header
    header = " | ".join(field.ljust(col_widths[field]) for field in fields)
    print(header)
    print("-+-".join("-" * col_widths[field] for field in fields))

    # Rows
    for r in rows:
        line = " | ".join(str(r.get(field, "")).ljust(col_widths[field]) for field in fields)
        print(line)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate inventory and shopping list for the Smart Incubator."
    )
    parser.add_argument(
        "-n",
        "--units",
        type=int,
        default=1,
        help="Number of incubator units / PCBs to build (default: 1).",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Include optional components from the parts list.",
    )
    parser.add_argument(
        "--include-tools",
        action="store_true",
        help="Include tools & consumables in the shopping list.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format for the shopping list (default: table).",
    )
    parser.add_argument(
        "--init-inventory",
        action="store_true",
        help="Run an interactive inventory data input wizard and write JSON.",
    )
    parser.add_argument(
        "--teardown-no-tec1",
        action="store_true",
        help="Use the simplified teardown BOM (no TEC1) for interactive inventory.",
    )
    parser.add_argument(
        "--inventory-file",
        type=str,
        default="inventory_data.json",
        help="Path for the inventory JSON file (default: inventory_data.json).",
    )

    args = parser.parse_args(argv)

    if args.init_inventory:
        output_path = Path(args.inventory_file)
        if args.teardown_no_tec1:
            interactive_teardown_inventory_setup(output_path=output_path)
        else:
            interactive_inventory_setup(
                output_path=output_path,
                include_optional=args.include_optional,
                include_tools=args.include_tools,
            )
        return

    shopping = compute_shopping_list(
        units=args.units,
        include_optional=args.include_optional,
        include_tools=args.include_tools,
    )

    if args.format == "json":
        print(json.dumps(shopping, indent=2))
        return

    if args.format == "csv":
        # Emit two CSV sections: parts and pcb
        writer = csv.writer(
            open("shopping_list_parts.csv", "w", newline="", encoding="utf-8")
        )
        part_fields = [
            "component",
            "specification",
            "quantity_per_unit_raw",
            "quantity_per_unit_numeric",
            "total_quantity_numeric",
            "approx_cost",
            "notes",
            "section",
            "subsection",
            "optional",
            "tool",
        ]
        writer.writerow(part_fields)
        for row in shopping["parts"]:
            writer.writerow([row.get(f, "") for f in part_fields])

        pcb_writer = csv.writer(
            open("shopping_list_pcb.csv", "w", newline="", encoding="utf-8")
        )
        pcb_fields = ["lib_id", "value", "count_per_unit", "total_count"]
        pcb_writer.writerow(pcb_fields)
        for row in shopping["pcb"]:
            pcb_writer.writerow([row.get(f, "") for f in pcb_fields])

        print("Wrote shopping_list_parts.csv and shopping_list_pcb.csv")
        return

    # Default: human-readable tables
    print(f"\n=== Smart Incubator Shopping List for {args.units} unit(s) ===\n")

    print(">> High-level parts (Docs/parts_list.md)\n")
    part_fields = [
        "component",
        "specification",
        "quantity_per_unit_raw",
        "total_quantity_numeric",
        "approx_cost",
        "section",
    ]
    _print_table(shopping["parts"], part_fields)

    print("\n>> PCB components (from KiCad schematic)\n")
    pcb_fields = ["lib_id", "value", "count_per_unit", "total_count"]
    _print_table(shopping["pcb"], pcb_fields)


if __name__ == "__main__":
    main()
