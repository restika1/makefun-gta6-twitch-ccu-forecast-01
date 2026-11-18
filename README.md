[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/restika1/makefun-gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/restika1/makefun-gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast GTA VI launch-day Twitch concurrent viewers hour-by-hour (hours 2–24 UTC, 19 Nov 2026) from the first hour's count. Uses weighted comparable curves from midnight-local rolling launches (ELDEN RING, Resident Evil Requiem, Ghost of Yōtei, Monster Hunter Wilds, Zelda TOTK, etc.) aligned by unlock timezone waves (NZ 11Z → US-W 8Z). Computes per-hour median ratios and log-spread quantiles from the comparable distribution, scaled to the case's hour-1 print. Validated on four practice cases (Marvel's Wolverine, RDR2, GoW Ragnarök, Spider-Man 2) — all outputs valid (23 hours, non-decreasing quantiles, ≤65KB, deterministic), clearly beating the persistence baseline (~0.387 pinball loss).

Run locally:
```bash
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Competition: https://make.fun/bounty/gta6-twitch-ccu-forecast-01