"""
tokenomics_simulator.py

Token emission and unlock schedule simulator for DeFi tokenomics DD.

Takes a YAML or JSON config with token allocation buckets (team, investors,
treasury, community, liquidity, etc.) and produces a month-by-month emission
schedule plus structural risk flags.

What it answers:
  1. What % of total supply unlocks in the first 12 months?
  2. What is the inflation curve (circulating supply over 60 months)?
  3. Where are the cliff drops (single-day unlocks above N% of supply)?
  4. What is the sell pressure score per quarter?

Usage:
    python tokenomics_simulator.py config.yaml
    python tokenomics_simulator.py config.yaml --months 60 --out report.json

Sample config in examples/sample_protocol.yaml.

Author: Denis Chaplinskii
Repo: https://github.com/denhealthy/tokenomics-simulator
License: MIT
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_config(path: str) -> Dict[str, Any]:
    p = Path(path)
    raw = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        if not yaml:
            sys.exit("install PyYAML for yaml configs: pip install pyyaml")
        return yaml.safe_load(raw)
    return json.loads(raw)


def linear_release(allocation: float, cliff: int, vesting: int, months: int) -> List[float]:
    """Return monthly release amounts for a linear vest with optional cliff."""
    release = [0.0] * months
    if vesting <= 0:
        if cliff < months:
            release[cliff] = allocation
        return release
    per_month = allocation / vesting
    for i in range(vesting):
        idx = cliff + i
        if idx >= months:
            break
        release[idx] = per_month
    return release


def cliff_release(allocation: float, cliff: int, months: int) -> List[float]:
    """Single-day unlock at cliff month."""
    release = [0.0] * months
    if 0 <= cliff < months:
        release[cliff] = allocation
    return release


def simulate(config: Dict[str, Any], months: int = 60) -> Dict[str, Any]:
    total_supply = float(config.get("total_supply", 0))
    buckets = config.get("buckets", [])

    schedule_per_bucket: Dict[str, List[float]] = {}
    for b in buckets:
        name = b["name"]
        allocation = total_supply * (b["allocation_pct"] / 100.0)
        cliff = int(b.get("cliff_months", 0))
        vesting = int(b.get("vesting_months", 0))
        unlock_type = b.get("unlock_type", "linear")

        if unlock_type == "tge":
            sched = cliff_release(allocation, 0, months)
        elif unlock_type == "cliff":
            sched = cliff_release(allocation, cliff, months)
        else:
            sched = linear_release(allocation, cliff, vesting, months)

        schedule_per_bucket[name] = sched

    total_per_month = [
        sum(sched[m] for sched in schedule_per_bucket.values()) for m in range(months)
    ]
    cumulative = []
    running = 0.0
    for v in total_per_month:
        running += v
        cumulative.append(running)

    circulating_pct = [round(c / total_supply * 100, 2) if total_supply else 0 for c in cumulative]

    flags = []
    if circulating_pct[11] > 40:
        flags.append({
            "level": "high_risk",
            "code": "year1_inflation_high",
            "note": f"{circulating_pct[11]}% of supply circulating by month 12. inflation pressure is structurally aggressive.",
        })
    elif circulating_pct[11] > 25:
        flags.append({
            "level": "watch",
            "code": "year1_inflation_moderate",
            "note": f"{circulating_pct[11]}% circulating by month 12. moderate inflation, monitor unlock cliffs.",
        })

    for m, amount in enumerate(total_per_month):
        if total_supply and (amount / total_supply) > 0.05:
            flags.append({
                "level": "high_risk",
                "code": "cliff_drop",
                "month": m,
                "amount_pct": round(amount / total_supply * 100, 2),
                "note": f"single-month unlock of {round(amount/total_supply*100,2)}% of total supply at month {m}. expect sharp sell pressure.",
            })

    quarterly_supply = []
    for q in range(months // 3):
        start = q * 3
        end = start + 3
        q_amount = sum(total_per_month[start:end])
        quarterly_supply.append({
            "quarter": q + 1,
            "unlocked_pct": round(q_amount / total_supply * 100, 2) if total_supply else 0,
            "cumulative_pct": round(sum(total_per_month[: end]) / total_supply * 100, 2) if total_supply else 0,
        })

    return {
        "total_supply": total_supply,
        "months_simulated": months,
        "circulating_pct_by_month": circulating_pct,
        "monthly_unlocks": [round(v, 2) for v in total_per_month],
        "quarterly": quarterly_supply,
        "flags": flags,
        "summary": summarize(flags, circulating_pct, months),
    }


def summarize(flags: List[Dict], circulating_pct: List[float], months: int) -> Dict[str, Any]:
    overall = "ok"
    if any(f["level"] == "high_risk" for f in flags):
        overall = "high_risk"
    elif any(f["level"] == "watch" for f in flags):
        overall = "watch"

    return {
        "overall_flag": overall,
        "year_1_circulating_pct": circulating_pct[min(11, months - 1)],
        "year_2_circulating_pct": circulating_pct[min(23, months - 1)],
        "year_3_circulating_pct": circulating_pct[min(35, months - 1)],
        "full_dilution_month": next(
            (m for m, v in enumerate(circulating_pct) if v >= 99.5), None
        ),
        "flag_count": len(flags),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Tokenomics emission and unlock schedule simulator for DD."
    )
    parser.add_argument("config", help="path to YAML or JSON config")
    parser.add_argument("--months", type=int, default=60, help="months to simulate (default 60)")
    parser.add_argument("--out", default="-", help="output file path or '-' for stdout")
    args = parser.parse_args()

    config = load_config(args.config)
    result = simulate(config, months=args.months)

    output = json.dumps(result, indent=2)
    if args.out == "-":
        print(output)
    else:
        Path(args.out).write_text(output)
        print(f"written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
