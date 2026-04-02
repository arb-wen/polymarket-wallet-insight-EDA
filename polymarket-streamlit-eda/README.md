# Polymarket Wallet Insight

[简体中文](./README.zh-CN.md)

A bilingual Streamlit dashboard for wallet-level Polymarket analysis.  
It turns a single wallet address into a research view with trade-flow EDA, positions, PnL, and behavioral user tags.

## What It Does

- Input one Polymarket wallet address
- Choose a fetch size: `1000 / 3000 / 5000 / 10000`
- Pull recent wallet trade activity from the official Polymarket Data API
- Enrich trades with event tags from the official event API
- Show current positions, realized PnL, unrealized PnL, and total PnL
- Generate composite user tags such as `Sports High-Frequency Maker` or `Politics Event Sniper`
- Export filtered raw trade data as CSV

## Key Features

- Wallet-centric trade-flow dashboard
- Bilingual UI: English / Simplified Chinese
- Up to `10,000` recent trades with time-window pagination for active wallets
- Apple-inspired visual style with responsive Streamlit layout
- Category and sports breakdown pies
- Activity timeline, heatmap, trade tape, and price distribution
- Current positions panel powered by official `positions` and `closed-positions` endpoints
- Heuristic behavioral labeling based on execution style, concentration, low-price buying, and PnL state

## Data Sources

This project uses official Polymarket APIs:

- [API introduction](https://docs.polymarket.com/api-reference/introduction)
- [Get user activity](https://docs.polymarket.com/api-reference/core/get-user-activity)
- [Get current positions for a user](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)
- [Get closed positions for a user](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user)
- [Get event by slug](https://docs.polymarket.com/api-reference/events/get-event-by-slug)

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Recommended Fetch Size

- `5000` is the best default for most wallets
- `10000` is the deep-analysis mode
- Very active bots may take noticeably longer on the first load because the app also fetches positions and closed positions

## Project Structure

```text
app.py              Main Streamlit app
README.md           English README
README.zh-CN.md     Chinese README
.streamlit/         Streamlit theme config
```

## Notes

- No API key is currently required for the public Polymarket endpoints used here
- Cold loads for extremely active wallets are slower than cached reloads
- PnL values follow the official Polymarket positions endpoints instead of being fully reconstructed from sampled trades alone
