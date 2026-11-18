"""gta6-twitch-ccu-forecast-01: forecast GTA VI launch-day Twitch viewers hour by hour.

Model: uses comparable launches with midnight-local rolling unlocks (like GTA VI).
Aligns daily curves by unlock timezone, computes median curve + quantile spreads,
scales to the case's hour-1 print. Deterministic (no randomness).
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# Comparable weights based on similarity to GTA VI's unlock pattern:
# midnight local rolling (NZ ~11Z, EU ~23Z, UK 0Z, US-E 5Z, US-W 8Z)
# Higher weight = more similar unlock pattern and game tier
COMPARABLE_WEIGHTS = {
    "ELDEN RING": 1.0,           # Best match: NZ 11Z, EU 23Z, UK 0Z, US-E 5Z, US-W 8Z
    "Resident Evil Requiem": 0.9, # Midnight local rolling, US Eastern-equivalent
    "Ghost of Yōtei": 0.9,        # Midnight local rolling, US Eastern midnight
    "Monster Hunter Wilds": 0.8,  # Consoles midnight local, Steam global 5Z
    "The Legend of Zelda: Tears of the Kingdom": 0.7,  # Midnight local, NA simultaneous at US-E midnight
    "FINAL FANTASY VII REBIRTH": 0.6,  # Sony midnight local expected
    "The Last of Us Part II": 0.6,     # Sony midnight local expected
    "Assassin's Creed Shadows": 0.5,   # Delayed, early access but standard midnight local
    "Cyberpunk 2077": 0.4,      # PC simultaneous 0Z, consoles midnight local
    "Hogwarts Legacy": 0.3,     # Early access contaminated
    "Starfield": 0.2,           # Early access contaminated
    "Diablo IV": 0.2,           # Early access contaminated
    "Forza Horizon 5": 0.1,     # Early access contaminated
    "DOOM: The Dark Ages": 0.1, # Early access contaminated
}

# Hours 2-24 (indices 0-22 correspond to hours 2-24)
HOURS = list(range(2, 25))

def round2(x: float) -> float | int:
    """Round to 2 decimals, half up. Whole numbers returned as int."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def extract_release_day_curve(comparable: dict) -> list[float] | None:
    """Extract 24-hour release day curve (hours 1-24), normalized by hour 1.
    Returns list of 24 ratios, or None if insufficient data."""
    hourly = comparable.get("hourly", [])
    day_start = comparable["day_start"][:10]  # YYYY-MM-DD
    
    # Get the 24 hours of release day
    release_day = [h for h in hourly if h["from"].startswith(day_start)]
    if len(release_day) < 24:
        return None
    
    release_day = release_day[:24]
    hour1_viewers = release_day[0]["viewers"]
    if hour1_viewers <= 0:
        return None
    
    return [h["viewers"] / hour1_viewers for h in release_day]


def build_model_curves(case: dict) -> tuple[list[float], list[list[float]]]:
    """Build median curve and quantile spreads from comparables.
    Returns (median_ratios[23], quantile_spreads[23][5]) for hours 2-24."""
    
    # Extract curves from weighted comparables
    curves = []  # list of (weight, ratios[24])
    for c in case["comparables"]:
        name = c["name"]
        weight = COMPARABLE_WEIGHTS.get(name, 0.0)
        if weight <= 0:
            continue
        curve = extract_release_day_curve(c)
        if curve is not None:
            curves.append((weight, curve))
    
    if not curves:
        # Fallback: persistence baseline
        median = [1.0] * 23
        spreads = [[0.15 * math.sqrt(h - 1)] * 5 for h in HOURS]
        return median, spreads
    
    # Compute weighted median and quantiles for each hour (2-24)
    median_ratios = []
    quantile_values = []  # [hour][level] = value
    
    for h_idx in range(1, 24):  # hours 2-24 (index 1-23 in 0-based 24-hour curve)
        # Collect weighted values
        values = []
        weights = []
        for weight, curve in curves:
            values.append(curve[h_idx])
            weights.append(weight)
        
        # Weighted quantiles
        sorted_pairs = sorted(zip(values, weights))
        total_weight = sum(weights)
        
        hour_quantiles = []
        for level in LEVELS:
            target = level * total_weight
            cum = 0.0
            q_val = sorted_pairs[-1][0]
            for val, w in sorted_pairs:
                cum += w
                if cum >= target:
                    q_val = val
                    break
            hour_quantiles.append(q_val)
        
        quantile_values.append(hour_quantiles)
        median_ratios.append(hour_quantiles[2])  # median is at index 2 (level 0.5)
    
    # Convert quantiles to log spreads around median
    # q_tau = median * exp(z_tau * spread) => spread = ln(q_tau / median) / z_tau
    spreads = []
    for h in range(23):
        med = median_ratios[h]
        hour_spreads = []
        for tau_idx, level in enumerate(LEVELS):
            z = Z[tau_idx]
            q_val = quantile_values[h][tau_idx]
            if z == 0:
                spread = 0.0
            else:
                ratio = q_val / med if med > 0 else 1.0
                ratio = max(0.01, min(100, ratio))  # clamp
                spread = math.log(ratio) / z
            hour_spreads.append(spread)
        spreads.append(hour_spreads)
    
    return median_ratios, spreads


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    
    median_ratios, spreads = build_model_curves(case)
    
    hours_out = []
    for i, hour in enumerate(HOURS):
        med_ratio = median_ratios[i]
        hour_spreads = spreads[i]
        q = [round2(p1 * med_ratio * math.exp(z * s)) for z, s in zip(Z, hour_spreads)]
        # Ensure non-decreasing
        for j in range(1, 5):
            if q[j] < q[j-1]:
                q[j] = q[j-1]
        # Clamp to valid range
        q = [max(0.01, min(1e9, v)) for v in q]
        hours_out.append({"hour": hour, "q": q})
    
    return {"hours": hours_out}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()