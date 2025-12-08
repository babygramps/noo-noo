#!/usr/bin/env python3
"""
Interactive helper to estimate kg_per_division (slope) for TLB4 channels.

Procedure:
1) Connects to the TLB4 using the existing Modbus interface/protocol.
2) Samples raw channel values with EMPTY load cells.
3) Prompts you to place a known weight across all 4 load cells.
4) Samples again and computes the common kg_per_division.

Assumption: All four channels share the same slope. Weight distribution may be
uneven, but the common slope is derived from the total raw delta:
    kg_per_division = (sum of raw deltas for CH1-CH4) / known_weight_kg

Run:
    python scripts/tlb4_slope_helper.py --port COM4 --weight 10
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Make imports work no matter where the script is run from
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT / "src"))

from epdm_vacuum.config.settings import get_settings, create_tlb4_config_from_settings
from epdm_vacuum.daq.modbus_interface import ModbusInterface


def sample_raw(interface: ModbusInterface, samples: int = 10, delay: float = 0.2) -> Tuple[List[int], float]:
    """Read averaged raw channel values."""
    agg = [0.0, 0.0, 0.0, 0.0]
    for _ in range(samples):
        data = interface.read()
        for i in range(4):
            agg[i] += float(data.get(f"load_cell_{i+1}_raw", 0))
        time.sleep(delay)
    avg = [int(a / samples) for a in agg]
    return avg, time.time()


def main() -> None:
    parser = argparse.ArgumentParser(description="TLB4 slope helper (kg_per_division estimator)")
    parser.add_argument("--port", default=None, help="Serial port (e.g., COM4 or /dev/ttyUSB0). Defaults to config, then auto.")
    parser.add_argument("--weight", type=float, default=10.0, help="Known weight in kg placed across all 4 cells.")
    parser.add_argument("--samples", type=int, default=12, help="Samples to average for each phase.")
    args = parser.parse_args()

    settings = get_settings()
    tlb4_config = create_tlb4_config_from_settings(settings)

    # Resolve port: CLI > config > platform-default (/dev/ttyUSB0 on Linux, COM4 on Windows)
    port = args.port or settings.get("hardware", "modbus", "tlb4", "port", default=None)
    if not port:
        if sys.platform.startswith("linux"):
            port = "/dev/ttyUSB0"
        elif sys.platform.startswith("win"):
            port = "COM4"
        else:
            port = "/dev/ttyUSB0"
    print(f"Using port: {port}")
    print(f"Known weight: {args.weight:.2f} kg (across all 4 channels)")
    print(f"Registers (from config): CH1={tlb4_config.reg_channel_1}, CH2={tlb4_config.reg_channel_2}, "
          f"CH3={tlb4_config.reg_channel_3}, CH4={tlb4_config.reg_channel_4}")

    interface = ModbusInterface(
        port=port,
        slave_address=1,
        baudrate=9600,
        timeout=1.0,
        parity="None",
        databits=8,
        stopbits=1,
        tlb4_config=tlb4_config,
    )

    if not interface.connect():
        print("Failed to connect to TLB4. Check port and wiring.")
        sys.exit(1)

    try:
        input("Ensure load cells are EMPTY, then press Enter to sample baseline...")
        empty_raw, t0 = sample_raw(interface, samples=args.samples)

        print("\nBaseline (empty) raw averages:")
        print(f"  CH1={empty_raw[0]}, CH2={empty_raw[1]}, CH3={empty_raw[2]}, CH4={empty_raw[3]}")

        input(f"Place {args.weight:.2f} kg across all 4 load cells, let it stabilize, then press Enter...")
        loaded_raw, t1 = sample_raw(interface, samples=args.samples)

        print("\nLoaded raw averages:")
        print(f"  CH1={loaded_raw[0]}, CH2={loaded_raw[1]}, CH3={loaded_raw[2]}, CH4={loaded_raw[3]}")

        deltas = [loaded_raw[i] - empty_raw[i] for i in range(4)]
        total_delta = sum(deltas)

        print("\nDelta (loaded - empty):")
        print(f"  CH1={deltas[0]}, CH2={deltas[1]}, CH3={deltas[2]}, CH4={deltas[3]}")
        print(f"  Total delta = {total_delta}")

        if total_delta <= 0:
            print("Total delta is non-positive; check that the weight is applied and registers are correct.")
            return

        kg_per_division = total_delta / args.weight

        print("\nSuggested scaling:")
        print(f"  kg_per_division (common for all channels) = {kg_per_division:.2f} raw divisions per kg")
        print("\nTo apply in config (hardware_config.yaml -> hardware.modbus.tlb4.channel_scaling.kg_per_division):")
        print(f"  kg_per_division: {kg_per_division:.2f}")

        print("\nNotes:")
        print("- Calculation uses total raw delta, so uneven weight distribution is handled automatically.")
        print("- If you repeat the test, take the average of multiple runs.")
        print("- For fine tuning, you can also run span_calibration in the Modbus interface.")

    finally:
        interface.disconnect()


if __name__ == "__main__":
    main()

