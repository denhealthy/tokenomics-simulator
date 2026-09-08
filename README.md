# tokenomics-simulator

Token emission and unlock schedule simulator for DeFi DD memos.

The single most useful pre-investment check is: "what % of total supply unlocks in the first 12 months, and where are the cliff drops?". This script answers that in 5 seconds from a YAML config.

## What it does

Takes a YAML or JSON config describing token allocation buckets (team, investors, treasury, community, ecosystem grants, liquidity, future emissions). Each bucket has cliff and vesting parameters.

Outputs a structured report with:

1. **Circulating supply % by month** for 60 months (5 years)
2. **Monthly unlock amounts** in absolute tokens
3. **Quarterly breakdown** with cumulative percentages
4. **Risk flags:**
   - `year1_inflation_high` if more than 40% of supply circulates by month 12
   - `year1_inflation_moderate` between 25% and 40%
   - `cliff_drop` for any single-month unlock above 5% of total supply
5. **Summary** with year 1/2/3 circulating %, full dilution month, overall flag

## Install

Python 3.10+. Optional YAML support:

```bash
pip install pyyaml
```

JSON configs work without any dependency.

## Usage

```bash
python tokenomics_simulator.py examples/sample_protocol.yaml
```

Custom horizon:

```bash
python tokenomics_simulator.py config.yaml --months 84
```

Write to file:

```bash
python tokenomics_simulator.py config.yaml --out reports/protocol.json
```

## Config format

YAML or JSON. Schema in `examples/sample_protocol.yaml`. Key fields per bucket:

| Field | Type | Meaning |
|---|---|---|
| `name` | string | bucket label (team, investors, treasury, etc.) |
| `allocation_pct` | float | percentage of total supply allocated to this bucket |
| `cliff_months` | int | months before any tokens unlock |
| `vesting_months` | int | months over which the bucket vests linearly after cliff |
| `unlock_type` | string | `linear`, `cliff`, or `tge` |

Unlock types:

- `tge`: full bucket released at month 0
- `cliff`: full bucket released as single unlock at `cliff_months`
- `linear`: linear release over `vesting_months` starting at `cliff_months`

## Sample output

Run on the example config (hypothetical L2 with 1B supply):

```json
{
  "total_supply": 1000000000.0,
  "months_simulated": 60,
  "summary": {
    "overall_flag": "watch",
    "year_1_circulating_pct": 38.5,
    "year_2_circulating_pct": 61.2,
    "year_3_circulating_pct": 78.4,
    "full_dilution_month": 59,
    "flag_count": 1
  },
  "flags": [
    {
      "level": "watch",
      "code": "year1_inflation_moderate",
      "note": "38.5% circulating by month 12. moderate inflation, monitor unlock cliffs."
    }
  ],
  "quarterly": [
    {"quarter": 1, "unlocked_pct": 14.5, "cumulative_pct": 14.5},
    {"quarter": 2, "unlocked_pct": 8.7, "cumulative_pct": 23.2},
    {"quarter": 3, "unlocked_pct": 7.3, "cumulative_pct": 30.5}
  ]
}
```

## What this is for

The script is a **starting point** for a tokenomics review, not a complete answer. It tells you:

- Whether the team is loading early-year supply (high inflation pressure)
- Where the structural sell-pressure events are
- How "fully diluted" valuation translates to actual circulating valuation over time

It does NOT tell you:

- Whether the team will actually follow the published schedule (history shows many protocols modify it post-launch)
- Whether token utility is sufficient to absorb the unlocked supply
- Whether the treasury is governed responsibly
- Whether secondary market liquidity can handle the unlock cadence

Those layers need a human read. This script just shortcuts the math.

## Use cases

- **Pre-deal DD:** run on a target protocol's published tokenomics before deciding to dig deeper
- **Comparative analysis:** simulate two protocols side by side, compare year-1 inflation profiles
- **Stress testing:** modify the config to test "what if team unlock is brought forward by 6 months" scenarios
- **Public reporting:** generate quarterly emission breakdowns for portfolio companies

## Roadmap

- Linear-with-bonding-curve releases (some protocols use quadratic vesting)
- Burn mechanics integration (offset unlocks with burn rates)
- Multi-chain emissions (separate L1 and L2 schedules for the same token)
- CSV output for spreadsheet workflows

## License

MIT.

