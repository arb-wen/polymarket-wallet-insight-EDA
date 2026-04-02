from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import re
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

APP_TZ = "Asia/Shanghai"
DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
DEFAULT_LIMIT = 10_000
DEFAULT_FETCH_SIZE = 5_000
FETCH_LIMIT_OPTIONS = (1_000, 3_000, 5_000, 10_000)
REQUEST_TIMEOUT = 25
TRADE_PAGE_LIMIT = 500
TRADE_WINDOW_OFFSET_LIMIT = 3_000
POSITIONS_PAGE_LIMIT = 500
CLOSED_POSITIONS_PAGE_LIMIT = 50
CLOSED_POSITIONS_MAX_OFFSET = 5_000
POSITIONS_FETCH_BATCHES = 8
TRADE_FETCH_RETRIES = 5
TRADE_FETCH_BACKOFF_BASE_SECONDS = 0.75
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
LANG_OPTIONS = ("en", "zh-CN")
MAX_EVENT_FETCH_WORKERS = 8

PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}
SIDE_COLORS = {"BUY": "#7da8ff", "SELL": "#b7bec9"}
WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
WEEKDAY_LABELS = {
    "en": WEEKDAY_ORDER,
    "zh-CN": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
}
CATEGORY_LABELS = {
    "sports": {"en": "Sports", "zh-CN": "体育"},
    "politics": {"en": "Politics", "zh-CN": "政治"},
    "weather": {"en": "Weather", "zh-CN": "天气"},
    "crypto": {"en": "Crypto", "zh-CN": "加密"},
    "economy": {"en": "Economy", "zh-CN": "经济"},
    "culture": {"en": "Culture", "zh-CN": "文化娱乐"},
    "world": {"en": "World", "zh-CN": "国际"},
    "other": {"en": "Other", "zh-CN": "其他"},
}
SPORTS_LABELS = {
    "epl": {"en": "EPL", "zh-CN": "英超"},
    "la_liga": {"en": "La Liga", "zh-CN": "西甲"},
    "champions_league": {"en": "Champions League", "zh-CN": "欧冠"},
    "nba": {"en": "NBA", "zh-CN": "NBA"},
    "wnba": {"en": "WNBA", "zh-CN": "WNBA"},
    "nfl": {"en": "NFL", "zh-CN": "NFL"},
    "mlb": {"en": "MLB", "zh-CN": "MLB"},
    "nhl": {"en": "NHL", "zh-CN": "NHL"},
    "soccer": {"en": "Soccer", "zh-CN": "足球"},
    "basketball": {"en": "Basketball", "zh-CN": "篮球"},
    "tennis": {"en": "Tennis", "zh-CN": "网球"},
    "golf": {"en": "Golf", "zh-CN": "高尔夫"},
    "f1": {"en": "F1", "zh-CN": "F1"},
    "mma": {"en": "MMA / UFC", "zh-CN": "综合格斗 / UFC"},
    "boxing": {"en": "Boxing", "zh-CN": "拳击"},
    "cricket": {"en": "Cricket", "zh-CN": "板球"},
    "college_football": {"en": "College Football", "zh-CN": "大学橄榄球"},
    "college_basketball": {"en": "College Basketball", "zh-CN": "大学篮球"},
    "other_sports": {"en": "Other Sports", "zh-CN": "其他体育"},
}
CATEGORY_COLORS = {
    "sports": "#8db3ff",
    "politics": "#3a3a3c",
    "weather": "#bfd3ff",
    "crypto": "#8e8e93",
    "economy": "#6e6e73",
    "culture": "#d1d1d6",
    "world": "#a1a1aa",
    "other": "#e5e7eb",
}
SPORTS_COLORS = {
    "epl": "#7aa6ff",
    "la_liga": "#99b9ff",
    "champions_league": "#5f84d6",
    "nba": "#4f6ca8",
    "wnba": "#adb8d6",
    "nfl": "#44474f",
    "mlb": "#c5cfde",
    "nhl": "#7f8795",
    "soccer": "#d1d7e3",
    "basketball": "#909bb2",
    "tennis": "#bbc7dc",
    "golf": "#dce3ef",
    "f1": "#69758d",
    "mma": "#8fa2c7",
    "boxing": "#aeb9ce",
    "cricket": "#cdd7e8",
    "college_football": "#5b6270",
    "college_basketball": "#9aa5ba",
    "other_sports": "#e5e7eb",
}
TRANSLATIONS = {
    "en": {
        "language": "Language",
        "app_title": "Polymarket Wallet Flow",
        "scope_heading": "Scope",
        "scope_body": (
            "Enter one Polymarket wallet address and the app will fetch up to the latest `{limit}` trades "
            "from the official Data API. This MVP is intentionally wallet-centric: it focuses on trading "
            "cadence, side bias, contract concentration, and raw trade inspection."
        ),
        "fetch_limit_label": "Fetch size",
        "fetch_limit_help": "Choose how many recent trades to load. 5,000 is the best default for speed and depth.",
        "wallet_input_label": "Wallet address",
        "wallet_input_help": "Paste a Polymarket wallet address. The app will fetch up to {limit} recent trades for that wallet.",
        "load_button": "Load",
        "fetch_spinner": "Fetching up to {limit} wallet trades, positions, and event tags from Polymarket...",
        "fetch_failed": "Fetch failed: {error}",
        "empty_wallet": "No trades were returned for this wallet.",
        "empty_filters": "No trades match the current filters.",
        "invalid_address": "Enter a valid EVM address, for example 0x1234...abcd.",
        "hero_eyebrow": "Wallet Trade Flow",
        "hero_subtitle": (
            "Visual snapshot of the latest {limit} Polymarket trades for a single wallet. "
            "The dashboard emphasizes cadence, size, side bias, and contract concentration."
        ),
        "tracked_wallet": "Tracked Wallet",
        "sampled_notional": "Sampled Notional",
        "chip_recent_trades": "{count} recent trades",
        "chip_markets": "{count} markets",
        "chip_events": "{count} events",
        "chip_day_sample": "{count} day sample",
        "kpi_recent_trades": "Recent Trades",
        "kpi_recent_trades_note": "Most recent trades returned by the official Data API",
        "kpi_sampled_notional": "Sampled Notional",
        "kpi_sampled_notional_note": "Average trade {value}",
        "kpi_distinct_markets": "Distinct Markets",
        "kpi_distinct_markets_note": "Across {count} events",
        "kpi_buy_pressure": "Buy Pressure",
        "kpi_buy_pressure_note": "Sell notional {value}",
        "focus_contracts_heading": "Focus Contracts",
        "focus_contracts_note": "{count} trades | avg price {price}",
        "activity_timeline_title": "Daily Activity Timeline",
        "activity_timeline_y_left": "Sampled notional",
        "activity_timeline_y_right": "Trades",
        "trade_count": "Trade count",
        "top_contracts_title": "Top Contracts By Sampled Notional",
        "top_contracts_x": "Sampled notional",
        "heatmap_title": "Time-of-Week Heatmap",
        "category_mix_title": "Category Mix Of Latest Trades",
        "sports_mix_title": "Sports Mix Within Latest Trades",
        "sports_mix_heading": "Sports Breakdown",
        "profile_heading": "Execution Style",
        "profile_tag_heading": "User Tag",
        "profile_title_taker": "Taker-leaning",
        "profile_title_maker": "Maker-leaning",
        "profile_title_mixed": "Mixed / unclear",
        "profile_tendency_taker": "Taker",
        "profile_tendency_maker": "Maker",
        "profile_tendency_mixed": "Neutral",
        "profile_archetype_pattern": "{category}-led {tendency}",
        "profile_primary_category": "Primary category",
        "profile_primary_category_share": "Category share",
        "profile_primary_sport": "Top sports bucket",
        "profile_primary_sport_share": "Sports bucket share",
        "profile_note_taker": "More than 50% of sampled trade sizes are integers, so this wallet is classified as Taker-leaning.",
        "profile_note_maker": "More than 50% of sampled trade sizes have decimals, so this wallet is classified as Maker-leaning.",
        "profile_note_mixed": "Integer-sized and decimal-sized trades are evenly split, so the profile stays neutral.",
        "profile_rule": "Heuristic: based on trade `size`, not notional.",
        "profile_integer_share": "Integer-size share",
        "profile_decimal_share": "Decimal-size share",
        "profile_integer_count": "Integer-size trades",
        "profile_decimal_count": "Decimal-size trades",
        "profile_chart_title": "Integer vs Decimal Trade Size Mix",
        "profile_style_title": "Primary style",
        "profile_style_reason": "Why this style",
        "profile_style_trades_per_day": "Trades / active day",
        "profile_style_low_price_buy_share": "Low-price buy share",
        "profile_style_top_event_share": "Top event share",
        "profile_behavior_high_frequency_maker": "High-Frequency Maker",
        "profile_behavior_high_frequency_taker": "High-Frequency Taker",
        "profile_behavior_event_sniper": "Event Sniper",
        "profile_behavior_low_price_accumulator": "Low-Price Accumulator",
        "profile_behavior_conviction_buyer": "Conviction Buyer",
        "profile_behavior_balanced_rotator": "Balanced Rotator",
        "profile_behavior_maker": "Maker",
        "profile_behavior_taker": "Taker",
        "profile_behavior_mixed": "Neutral",
        "profile_combo_pattern": "{category} {behavior}",
        "profile_reason_high_frequency_maker": "Trade count per active day is high and decimal-sized orders dominate, which looks closer to systematic quoting or layered entries.",
        "profile_reason_high_frequency_taker": "Trade count per active day is high and integer-sized orders dominate, which looks closer to aggressive sweeping or reactive execution.",
        "profile_reason_event_sniper": "A large share of the sample is concentrated in one event cluster, suggesting targeted event-driven trading rather than broad scanning.",
        "profile_reason_low_price_accumulator": "Most buy flow happens below 25%, which looks like repeated low-probability accumulation rather than balanced trading.",
        "profile_reason_conviction_buyer": "Buy-side notional dominates the sample, showing a directional wallet that tends to build inventory instead of recycling risk quickly.",
        "profile_reason_balanced_rotator": "Flow is spread across multiple markets with meaningful two-way trading, which looks closer to rotation than one-sided conviction.",
        "profile_reason_maker": "Decimal-sized trades dominate the sample, so the wallet still looks more Maker-like than directional.",
        "profile_reason_taker": "Integer-sized trades dominate the sample, so the wallet still looks more Taker-like than passive.",
        "profile_reason_mixed": "No single behavioral style is dominant enough, so the wallet stays neutral.",
        "profile_secondary_tags": "Secondary tags",
        "tag_high_frequency": "High-frequency",
        "tag_event_concentrated": "Event-concentrated",
        "tag_low_price_buyer": "Low-price buyer",
        "tag_buy_heavy": "Buy-heavy",
        "tag_profitable": "PnL-positive",
        "tag_underwater": "PnL-negative",
        "positions_heading": "PnL & Positions",
        "positions_note": "Built from Polymarket's current `positions` and `closed-positions` endpoints so the panel reflects both open inventory and historical realized outcomes.",
        "positions_open_value": "Open position value",
        "positions_open_value_note": "{count} live positions",
        "positions_unrealized_pnl": "Unrealized PnL",
        "positions_unrealized_pnl_note": "Across current inventory",
        "positions_realized_pnl": "Realized PnL",
        "positions_realized_pnl_note": "{count} closed positions + realized legs on open positions",
        "positions_total_pnl": "Total PnL",
        "positions_total_pnl_note": "Realized plus unrealized",
        "positions_current_title": "Current Positions",
        "positions_table_note": "Showing the top 40 open positions by current value.",
        "positions_chart_title": "Top Open Positions By Current Value",
        "positions_empty": "No current positions were returned for this wallet.",
        "positions_closed_empty": "No closed positions were returned for this wallet.",
        "positions_table_event": "Event",
        "positions_table_market": "Market",
        "positions_table_outcome": "Outcome",
        "positions_table_size": "Size",
        "positions_table_avg_price": "Avg price",
        "positions_table_cur_price": "Current price",
        "positions_table_cost_basis": "Cost basis",
        "positions_table_value": "Current value",
        "positions_table_unrealized": "Unrealized PnL",
        "positions_table_realized": "Realized PnL",
        "positions_table_total": "Total PnL",
        "positions_table_end_date": "End date",
        "positions_breakdown_value": "Current value",
        "positions_breakdown_total": "Total PnL",
        "trade_tape_title": "Trade Tape",
        "price_distribution_title": "Trade Price Distribution",
        "price_distribution_help_title": "How to read this chart",
        "price_distribution_help_body": (
            "The x-axis is trade price from 0% to 100%. Taller bars mean this wallet traded more often in that price zone. "
            "The box plot on top shows the median and the middle 50% range."
        ),
        "price_distribution_help_stats": "Sample median {median}, middle 50% {q1} to {q3}, full range {low} to {high}.",
        "price_label": "Trade price",
        "trades_label": "Trades",
        "most_active_contracts": "Most Active Contracts",
        "latest_trades": "Latest Trades",
        "raw_trades": "Raw Trades",
        "filters": "Filters",
        "market_search": "Market search",
        "market_search_placeholder": "Search by market title...",
        "side_filter": "Side",
        "events_filter": "Events",
        "minimum_notional": "Minimum notional",
        "date_range": "Date range",
        "download_csv": "Download filtered CSV",
        "tab_overview": "Overview",
        "tab_tape": "Trade Tape",
        "tab_raw": "Raw Data",
        "sources": "Sources",
        "table_contract": "Contract",
        "table_event": "Event",
        "table_trades": "Trades",
        "table_notional": "Notional",
        "table_avg_price": "Avg price",
        "table_first_seen": "First seen",
        "table_last_seen": "Last seen",
        "table_time": "Time",
        "table_market": "Market",
        "table_side": "Side",
        "table_outcome": "Outcome",
        "table_price": "Price",
        "table_size": "Size",
        "table_tx_hash": "Tx hash",
        "table_condition_id": "Condition ID",
        "side_buy": "BUY",
        "side_sell": "SELL",
        "side_unknown": "UNKNOWN",
    },
    "zh-CN": {
        "language": "语言",
        "app_title": "Polymarket 钱包交易流",
        "scope_heading": "范围",
        "scope_body": (
            "输入一个 Polymarket 钱包地址，页面会通过官方 Data API 抓取该地址最近最多 `{limit}` 笔交易。"
            "这个 MVP 以钱包画像为中心，重点展示交易节奏、买卖方向偏好、合约集中度和原始成交明细。"
        ),
        "fetch_limit_label": "抓取规模",
        "fetch_limit_help": "选择本次抓取的最近交易笔数。默认建议 5,000，速度和信息量更平衡。",
        "wallet_input_label": "钱包地址",
        "wallet_input_help": "输入一个 Polymarket 钱包地址，页面会自动抓取这个地址最近最多 {limit} 笔交易记录。",
        "load_button": "载入",
        "fetch_spinner": "正在从 Polymarket 拉取该钱包最近最多 {limit} 笔交易、持仓与事件标签数据...",
        "fetch_failed": "拉取失败：{error}",
        "empty_wallet": "这个钱包当前没有返回任何交易记录。",
        "empty_filters": "当前筛选条件下没有匹配的交易。",
        "invalid_address": "请输入合法的 EVM 地址，例如 0x1234...abcd。",
        "hero_eyebrow": "钱包交易流",
        "hero_subtitle": (
            "这是一个单钱包视角的可视化快照，覆盖最近 {limit} 笔 Polymarket 交易，"
            "重点看交易节奏、成交额、方向偏好和合约集中度。"
        ),
        "tracked_wallet": "跟踪钱包",
        "sampled_notional": "样本成交额",
        "chip_recent_trades": "最近 {count} 笔交易",
        "chip_markets": "{count} 个市场",
        "chip_events": "{count} 个事件",
        "chip_day_sample": "{count} 天样本",
        "kpi_recent_trades": "交易笔数",
        "kpi_recent_trades_note": "来自官方 Data API 返回的最新交易样本",
        "kpi_sampled_notional": "样本成交额",
        "kpi_sampled_notional_note": "平均每笔 {value}",
        "kpi_distinct_markets": "市场数量",
        "kpi_distinct_markets_note": "覆盖 {count} 个事件",
        "kpi_buy_pressure": "买入占比",
        "kpi_buy_pressure_note": "卖出成交额 {value}",
        "focus_contracts_heading": "重点合约",
        "focus_contracts_note": "{count} 笔交易 | 平均价格 {price}",
        "activity_timeline_title": "每日交易时间线",
        "activity_timeline_y_left": "样本成交额",
        "activity_timeline_y_right": "交易笔数",
        "trade_count": "交易笔数",
        "top_contracts_title": "成交额最高的合约",
        "top_contracts_x": "样本成交额",
        "heatmap_title": "一周活跃热力图",
        "category_mix_title": "最近交易的大类分布",
        "sports_mix_title": "体育交易内部联赛分布",
        "sports_mix_heading": "体育细分分布",
        "profile_heading": "执行风格画像",
        "profile_tag_heading": "用户标签",
        "profile_title_taker": "偏 Taker",
        "profile_title_maker": "偏 Maker",
        "profile_title_mixed": "中性 / 不明显",
        "profile_tendency_taker": "Taker",
        "profile_tendency_maker": "Maker",
        "profile_tendency_mixed": "中性",
        "profile_archetype_pattern": "{category}型 {tendency}",
        "profile_primary_category": "主导类别",
        "profile_primary_category_share": "类别占比",
        "profile_primary_sport": "主导体育子类",
        "profile_primary_sport_share": "体育子类占比",
        "profile_note_taker": "样本中超过 50% 的交易 size 是整数，因此按规则判断该钱包更偏向 Taker。",
        "profile_note_maker": "样本中超过 50% 的交易 size 带小数，因此按规则判断该钱包更偏向 Maker。",
        "profile_note_mixed": "整数 size 与小数 size 交易接近各占一半，因此这个画像暂时保持中性。",
        "profile_rule": "判定口径：基于每笔交易的 size，不是 notional。",
        "profile_integer_share": "整数下单占比",
        "profile_decimal_share": "小数下单占比",
        "profile_integer_count": "整数下单笔数",
        "profile_decimal_count": "小数下单笔数",
        "profile_chart_title": "整数 / 小数下单分布",
        "profile_style_title": "主风格标签",
        "profile_style_reason": "判定依据",
        "profile_style_trades_per_day": "活跃日均交易数",
        "profile_style_low_price_buy_share": "低价买入占比",
        "profile_style_top_event_share": "头部事件占比",
        "profile_behavior_high_frequency_maker": "高频 Maker",
        "profile_behavior_high_frequency_taker": "高频 Taker",
        "profile_behavior_event_sniper": "事件狙击型",
        "profile_behavior_low_price_accumulator": "低价区间扫货型",
        "profile_behavior_conviction_buyer": "单边建仓型",
        "profile_behavior_balanced_rotator": "轮动交易型",
        "profile_behavior_maker": "Maker",
        "profile_behavior_taker": "Taker",
        "profile_behavior_mixed": "中性",
        "profile_combo_pattern": "{category}{behavior}",
        "profile_reason_high_frequency_maker": "活跃日均交易数很高，且小数 size 下单占主导，更接近程序化挂单或分层吃流动性的 Maker 风格。",
        "profile_reason_high_frequency_taker": "活跃日均交易数很高，且整数 size 下单占主导，更接近主动扫单或追反应的 Taker 风格。",
        "profile_reason_event_sniper": "样本明显集中在少数事件簇上，说明这个钱包更像围绕特定事件集中出手，而不是广泛扫市场。",
        "profile_reason_low_price_accumulator": "多数买入发生在 25% 以下价格区间，更像是在反复吸纳低概率仓位，而不是均衡交易。",
        "profile_reason_conviction_buyer": "买入成交额显著高于卖出，说明这个钱包更偏向单边建仓，而不是快速来回轮动。",
        "profile_reason_balanced_rotator": "交易分散在多个市场，且双边都有明显成交，更像轮动切换，而不是单一方向押注。",
        "profile_reason_maker": "小数 size 交易占主导，因此这个钱包整体仍更接近 Maker。",
        "profile_reason_taker": "整数 size 交易占主导，因此这个钱包整体仍更接近 Taker。",
        "profile_reason_mixed": "没有任何一种行为特征占据足够优势，因此当前保持中性判断。",
        "profile_secondary_tags": "次级标签",
        "tag_high_frequency": "高频",
        "tag_event_concentrated": "事件集中",
        "tag_low_price_buyer": "低价吸筹",
        "tag_buy_heavy": "偏单边买入",
        "tag_profitable": "PnL 为正",
        "tag_underwater": "PnL 为负",
        "positions_heading": "PnL 与当前持仓",
        "positions_note": "基于 Polymarket 官方 `positions` 与 `closed-positions` 接口汇总，所以这里同时反映当前仓位和历史已实现结果。",
        "positions_open_value": "当前持仓市值",
        "positions_open_value_note": "{count} 个未平仓头寸",
        "positions_unrealized_pnl": "未实现 PnL",
        "positions_unrealized_pnl_note": "来自当前持仓浮盈浮亏",
        "positions_realized_pnl": "已实现 PnL",
        "positions_realized_pnl_note": "{count} 个已平仓头寸 + 未平仓仓位中的已实现部分",
        "positions_total_pnl": "总 PnL",
        "positions_total_pnl_note": "已实现与未实现合计",
        "positions_current_title": "当前持仓明细",
        "positions_table_note": "表格仅展示按当前市值排序的前 40 个未平仓头寸。",
        "positions_chart_title": "当前持仓市值 Top 头寸",
        "positions_empty": "这个钱包当前没有返回未平仓持仓。",
        "positions_closed_empty": "这个钱包当前没有返回已平仓持仓。",
        "positions_table_event": "事件",
        "positions_table_market": "市场",
        "positions_table_outcome": "结果",
        "positions_table_size": "持仓数量",
        "positions_table_avg_price": "持仓均价",
        "positions_table_cur_price": "当前价格",
        "positions_table_cost_basis": "成本",
        "positions_table_value": "当前市值",
        "positions_table_unrealized": "未实现 PnL",
        "positions_table_realized": "已实现 PnL",
        "positions_table_total": "总 PnL",
        "positions_table_end_date": "到期时间",
        "positions_breakdown_value": "当前市值",
        "positions_breakdown_total": "总 PnL",
        "trade_tape_title": "交易流气泡图",
        "price_distribution_title": "成交价格分布",
        "price_distribution_help_title": "怎么看这张图",
        "price_distribution_help_body": (
            "横轴是成交价格，范围从 0% 到 100%。柱子越高，说明这个价格区间成交越密集。"
            "上方箱线图表示中位数以及中间 50% 的主要成交区间。"
        ),
        "price_distribution_help_stats": "这位用户的样本中位价格是 {median}，中间 50% 集中在 {q1} 到 {q3}，整体范围是 {low} 到 {high}。",
        "price_label": "成交价格",
        "trades_label": "交易笔数",
        "most_active_contracts": "最活跃合约",
        "latest_trades": "最新交易",
        "raw_trades": "原始交易",
        "filters": "筛选器",
        "market_search": "市场搜索",
        "market_search_placeholder": "按市场标题搜索...",
        "side_filter": "方向",
        "events_filter": "事件",
        "minimum_notional": "最小成交额",
        "date_range": "日期范围",
        "download_csv": "下载当前筛选结果 CSV",
        "tab_overview": "总览",
        "tab_tape": "交易流",
        "tab_raw": "原始数据",
        "sources": "数据来源",
        "table_contract": "合约",
        "table_event": "事件",
        "table_trades": "交易笔数",
        "table_notional": "成交额",
        "table_avg_price": "平均价格",
        "table_first_seen": "首次出现",
        "table_last_seen": "最近出现",
        "table_time": "时间",
        "table_market": "市场",
        "table_side": "方向",
        "table_outcome": "结果",
        "table_price": "价格",
        "table_size": "数量",
        "table_tx_hash": "交易哈希",
        "table_condition_id": "Condition ID",
        "side_buy": "买入",
        "side_sell": "卖出",
        "side_unknown": "未知",
    },
}


class PolymarketAPIError(RuntimeError):
    """Raised when an upstream Polymarket endpoint fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class WalletContext:
    address: str
    alias: str
    profile_image: str


st.set_page_config(
    page_title="Polymarket Wallet Flow",
    page_icon=":money_with_wings:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --page: #f5f5f7;
            --surface: rgba(255, 255, 255, 0.84);
            --surface-strong: rgba(255, 255, 255, 0.94);
            --text: #111111;
            --muted: #6e6e73;
            --line: rgba(17, 17, 17, 0.08);
            --shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
            --shadow-soft: 0 4px 16px rgba(15, 23, 42, 0.03);
            --accent: #8db3ff;
            --accent-soft: rgba(141, 179, 255, 0.14);
            --accent-border: rgba(141, 179, 255, 0.28);
            --radius-xl: 28px;
            --radius-lg: 22px;
            --radius-md: 18px;
        }
        .stApp {
            background: linear-gradient(180deg, #f5f5f7 0%, #f3f4f6 100%);
            color: var(--text);
        }
        [data-testid="stDecoration"] {
            display: none;
        }
        [data-testid="stHeader"] {
            background: rgba(245, 245, 247, 0.92);
            border-bottom: 1px solid rgba(17, 17, 17, 0.05);
        }
        .main .block-container {
            max-width: 1220px;
            padding-top: 1.4rem;
            padding-bottom: 4rem;
        }
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
        }
        h1, h2, h3, h4, p, label, span, div {
            color: var(--text);
        }
        h1 {
            font-size: clamp(2.4rem, 5vw, 4rem);
            line-height: 1.02;
            letter-spacing: -0.045em;
            font-weight: 700;
            margin-bottom: 0.45rem;
        }
        h3 {
            font-size: 1.1rem;
            line-height: 1.2;
            letter-spacing: -0.02em;
            font-weight: 650;
        }
        .hero-shell {
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(260px, 0.82fr);
            gap: 1rem;
            padding: 1.25rem;
            border: 1px solid var(--line);
            border-radius: var(--radius-xl);
            background: var(--surface);
            backdrop-filter: blur(20px) saturate(135%);
            box-shadow: var(--shadow-soft);
            margin: 0.4rem 0 1.15rem;
            overflow: hidden;
            animation: apple-enter 420ms cubic-bezier(0.22, 1, 0.36, 1);
        }
        .hero-copy {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.9rem;
            padding: 0.35rem 0.2rem 0.35rem 0.15rem;
        }
        .eyebrow {
            display: inline-flex;
            width: fit-content;
            padding: 0.4rem 0.72rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: #33538d;
            font-size: 0.74rem;
            font-weight: 650;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .hero-title {
            margin: 0;
            font-size: clamp(2.6rem, 4.8vw, 4.4rem);
            line-height: 1.02;
            letter-spacing: -0.05em;
            color: var(--text);
        }
        .hero-subtitle {
            margin: 0;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.72;
            max-width: 52rem;
        }
        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.1rem;
        }
        .chip {
            padding: 0.46rem 0.78rem;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.9);
            color: #2c2c2e;
            font-size: 0.84rem;
            font-weight: 600;
        }
        .hero-panel {
            min-height: 250px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--accent-border);
            background: rgba(246, 249, 255, 0.88);
            color: var(--text);
            padding: 1.15rem 1.1rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
        }
        .panel-label {
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            opacity: 1;
        }
        .panel-address {
            font-size: 1rem;
            line-height: 1.6;
            word-break: break-all;
            font-weight: 600;
            color: var(--text);
        }
        .panel-stat {
            font-size: 2.1rem;
            font-weight: 700;
            line-height: 1.02;
            letter-spacing: -0.04em;
            color: #2f5eb8;
        }
        .kpi-card, .snapshot-card, .profile-card, [data-testid="stPlotlyChart"], [data-testid="stDataFrame"], [data-testid="stTable"] {
            animation: apple-enter 420ms cubic-bezier(0.22, 1, 0.36, 1);
        }
        .kpi-card, .snapshot-card {
            border: 1px solid var(--line);
            box-shadow: var(--shadow-soft);
            backdrop-filter: blur(18px);
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }
        .kpi-card {
            padding: 1.05rem 1.02rem 0.96rem;
            border-radius: var(--radius-lg);
            background: var(--surface-strong);
            min-height: 126px;
        }
        .kpi-label {
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 650;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.58rem;
        }
        .kpi-value {
            color: var(--text);
            font-size: 1.85rem;
            font-weight: 700;
            line-height: 1.08;
            letter-spacing: -0.04em;
        }
        .kpi-note {
            color: var(--muted);
            font-size: 0.9rem;
            margin-top: 0.42rem;
        }
        .profile-card {
            padding: 1.2rem 1.2rem;
            border-radius: var(--radius-xl);
            background: var(--surface-strong);
            border: 1px solid var(--line);
            box-shadow: var(--shadow-soft);
            min-height: 376px;
        }
        .profile-kicker {
            color: var(--muted);
            font-size: 0.75rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 650;
            margin-bottom: 0.6rem;
        }
        .profile-title {
            color: var(--text);
            font-size: clamp(2rem, 3vw, 2.8rem);
            line-height: 1.02;
            letter-spacing: -0.05em;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }
        .profile-note {
            color: var(--muted);
            font-size: 0.96rem;
            line-height: 1.6;
            margin-bottom: 0.9rem;
            max-width: 40rem;
        }
        .profile-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
        }
        .profile-chip {
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: #f7f8fa;
            border: 1px solid var(--line);
            color: #2c2c2e;
            font-size: 0.84rem;
            font-weight: 650;
        }
        .insight-card {
            padding: 1rem 1rem 0.92rem;
            border-radius: var(--radius-lg);
            background: var(--surface-strong);
            border: 1px solid var(--line);
            box-shadow: var(--shadow-soft);
            margin-bottom: 0.85rem;
        }
        .insight-title {
            font-size: 0.94rem;
            line-height: 1.2;
            color: var(--text);
            font-weight: 650;
            margin-bottom: 0.55rem;
        }
        .insight-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.68;
        }
        .snapshot-card {
            padding: 0.95rem 1rem;
            border-radius: var(--radius-md);
            background: var(--surface-strong);
            min-height: 120px;
        }
        .snapshot-title {
            font-size: 0.8rem;
            color: var(--muted);
            margin-bottom: 0.45rem;
            font-weight: 650;
        }
        .snapshot-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text);
            line-height: 1.1;
            margin-bottom: 0.3rem;
        }
        .snapshot-note {
            color: var(--muted);
            font-size: 0.88rem;
        }
        .stTextInput > div > div > input {
            border-radius: 16px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.9);
            color: var(--text);
            min-height: 3rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
            transition: border-color 180ms ease, box-shadow 180ms ease;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--accent-border);
            box-shadow: 0 0 0 4px rgba(141, 179, 255, 0.16);
        }
        div[data-testid="stPopover"] > button {
            border-radius: 16px;
            min-height: 3rem;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.9);
            color: var(--text);
            font-weight: 650;
            box-shadow: var(--shadow-soft);
            transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        }
        div[data-testid="stPopover"] > button p {
            color: var(--text);
            font-weight: 650;
            font-size: 0.96rem;
        }
        .stButton > button {
            border-radius: 16px;
            min-height: 3rem;
            border: 1px solid rgba(17,17,17,0.06);
            background: #111111;
            color: #ffffff !important;
            font-weight: 650;
            box-shadow: 0 6px 18px rgba(17, 17, 17, 0.08);
            transition: transform 180ms ease, box-shadow 180ms ease, opacity 180ms ease;
        }
        .stButton > button p, .stButton > button span {
            color: #ffffff !important;
            fill: #ffffff !important;
        }
        .stButton > button:hover, div[data-testid="stPopover"] > button:hover, .kpi-card:hover, .snapshot-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
        }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border-radius: var(--radius-lg);
            overflow: hidden;
            border: 1px solid var(--line);
            box-shadow: var(--shadow-soft);
            background: rgba(255,255,255,0.92);
        }
        [data-testid="stPlotlyChart"] {
            border-radius: var(--radius-lg);
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.88);
            box-shadow: var(--shadow-soft);
            padding: 0.2rem 0.35rem 0.25rem;
        }
        div[data-baseweb="tab-list"] {
            gap: 0.3rem;
            padding: 0.26rem;
            background: rgba(255,255,255,0.76);
            border-radius: 999px;
            border: 1px solid var(--line);
            width: fit-content;
            box-shadow: var(--shadow-soft);
            margin-bottom: 0.55rem;
        }
        button[role="tab"] {
            border-radius: 999px;
            padding: 0.42rem 1rem;
            transition: background 180ms ease, color 180ms ease, box-shadow 180ms ease;
        }
        button[role="tab"][aria-selected="true"] {
            background: rgba(255,255,255,0.96) !important;
            color: var(--text) !important;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        }
        button[role="tab"][aria-selected="false"] {
            color: var(--muted) !important;
        }
        [data-testid="stMarkdownContainer"] a {
            color: #4a7fe8;
            text-decoration: none;
        }
        [data-testid="stCaptionContainer"] {
            color: var(--muted);
        }
        @keyframes apple-enter {
            from {
                opacity: 0;
                transform: translateY(6px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        @media (max-width: 960px) {
            .hero-shell { grid-template-columns: 1fr; }
            .hero-title { font-size: clamp(2.2rem, 9vw, 3.2rem); }
            .main .block-container {
                padding-top: 1rem;
                padding-bottom: 2.8rem;
            }
            .hero-panel, .profile-card, .kpi-card, .snapshot-card {
                min-height: auto;
            }
            div[data-baseweb="tab-list"] {
                width: 100%;
                overflow-x: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_compact_number(value: float | int) -> str:
    numeric = float(value)
    abs_value = abs(numeric)
    if abs_value >= 1_000_000_000:
        return f"{numeric / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{numeric / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{numeric / 1_000:.1f}K"
    if numeric.is_integer():
        return f"{int(numeric)}"
    return f"{numeric:.2f}"


def format_usd(value: float | int) -> str:
    return f"${format_compact_number(value)}"


def format_signed_usd(value: float | int) -> str:
    numeric = float(value)
    if numeric > 0:
        return f"+${format_compact_number(numeric)}"
    if numeric < 0:
        return f"-${format_compact_number(abs(numeric))}"
    return "$0"


def short_wallet(wallet: str) -> str:
    return f"{wallet[:6]}...{wallet[-4:]}"


def truncate_text(value: str, max_length: int = 42) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3].rstrip()}..."


def slug_to_title(slug: str | None) -> str:
    if not slug:
        return "Unknown Event"
    return slug.replace("-", " ").title()


def build_metric_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{html.escape(label)}</div>
      <div class="kpi-value">{html.escape(value)}</div>
      <div class="kpi-note">{html.escape(note)}</div>
    </div>
    """


def build_snapshot_card(title: str, value: str, note: str) -> str:
    return f"""
    <div class="snapshot-card">
      <div class="snapshot-title">{html.escape(title)}</div>
      <div class="snapshot-value">{html.escape(value)}</div>
      <div class="snapshot-note">{html.escape(note)}</div>
    </div>
    """


def get_lang() -> str:
    return st.session_state.get("lang", "en")


def tr(key: str, **kwargs: Any) -> str:
    lang = get_lang()
    catalog = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = catalog.get(key, TRANSLATIONS["en"].get(key, key))
    return template.format(**kwargs)


def language_label(lang: str) -> str:
    return "🇺🇸 US" if lang == "en" else "🇨🇳 简体中文"


def localized_side_map() -> dict[str, str]:
    return {
        "BUY": tr("side_buy"),
        "SELL": tr("side_sell"),
        "UNKNOWN": tr("side_unknown"),
    }


def render_language_switcher() -> None:
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"

    current_lang = get_lang()
    _, right = st.columns([6, 1.2])
    with right:
        with st.popover(language_label(current_lang), use_container_width=True):
            selected_lang = st.radio(
                tr("language"),
                options=list(LANG_OPTIONS),
                index=list(LANG_OPTIONS).index(current_lang),
                format_func=language_label,
                label_visibility="collapsed",
            )
    if selected_lang != current_lang:
        st.session_state["lang"] = selected_lang
        st.rerun()


def normalize_tag(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    normalized = normalized.replace("&", "and").replace("/", "-").replace("_", "-")
    normalized = re.sub(r"[^a-z0-9\- ]+", "", normalized)
    normalized = normalized.replace(" ", "-")
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def localize_category(key: str) -> str:
    return CATEGORY_LABELS.get(key, CATEGORY_LABELS["other"]).get(get_lang(), CATEGORY_LABELS["other"]["en"])


def localize_sports_subcategory(key: str) -> str:
    return SPORTS_LABELS.get(key, SPORTS_LABELS["other_sports"]).get(get_lang(), SPORTS_LABELS["other_sports"]["en"])


def derive_primary_category(tags: list[dict[str, Any]]) -> str:
    normalized_tags = {
        normalize_tag(tag.get("slug")) or normalize_tag(tag.get("label"))
        for tag in tags
        if tag.get("slug") or tag.get("label")
    }
    normalized_tags.discard("all")
    if not normalized_tags:
        return "other"

    sports_keys = {
        "sports", "soccer", "epl", "premier-league", "la-liga", "champions-league", "ucl", "nba",
        "nba-finals", "nba-playoffs", "basketball", "wnba", "nfl", "mlb", "nhl", "tennis", "golf",
        "boxing", "mma", "ufc", "cricket", "f1", "formula-1", "formula1", "motorsport", "football",
        "baseball", "hockey", "college-football", "college-basketball", "cfb", "cbb", "ncaaf", "ncaab",
    }
    politics_keys = {
        "politics", "elections", "election", "trump", "white-house", "congress", "senate", "house",
        "governor", "mayor", "presidency", "campaign", "polling", "parliament", "supreme-court",
    }
    weather_keys = {"weather", "climate", "hurricane", "storm", "tornado", "snow", "rain"}
    crypto_keys = {"crypto", "bitcoin", "ethereum", "solana", "dogecoin", "xrp", "btc", "eth"}
    economy_keys = {"economy", "fed", "business", "stocks", "stock-market", "ai", "technology", "tech", "inflation", "recession"}
    culture_keys = {"culture", "pop-culture", "movies", "movie", "television", "tv", "music", "celebrity", "awards", "entertainment"}
    world_keys = {"world", "geopolitics", "middle-east", "ukraine", "russia", "china", "israel"}

    if normalized_tags & sports_keys:
        return "sports"
    if normalized_tags & politics_keys:
        return "politics"
    if normalized_tags & weather_keys:
        return "weather"
    if normalized_tags & crypto_keys:
        return "crypto"
    if normalized_tags & economy_keys:
        return "economy"
    if normalized_tags & culture_keys:
        return "culture"
    if normalized_tags & world_keys:
        return "world"
    return "other"


def derive_sports_subcategory(tags: list[dict[str, Any]]) -> str | None:
    normalized_tags = [
        normalize_tag(tag.get("slug")) or normalize_tag(tag.get("label"))
        for tag in tags
        if tag.get("slug") or tag.get("label")
    ]
    if not normalized_tags:
        return None

    priority_groups = [
        (
            {
                "epl": "epl",
                "premier-league": "epl",
                "english-premier-league": "epl",
                "la-liga": "la_liga",
                "champions-league": "champions_league",
                "ucl": "champions_league",
                "uefa-champions-league": "champions_league",
                "nba": "nba",
                "nba-finals": "nba",
                "nba-playoffs": "nba",
                "wnba": "wnba",
                "nfl": "nfl",
                "super-bowl": "nfl",
                "mlb": "mlb",
                "world-series": "mlb",
                "nhl": "nhl",
                "stanley-cup": "nhl",
                "college-football": "college_football",
                "cfb": "college_football",
                "ncaaf": "college_football",
                "college-basketball": "college_basketball",
                "cbb": "college_basketball",
                "ncaab": "college_basketball",
                "ufc": "mma",
                "mma": "mma",
                "boxing": "boxing",
                "cricket": "cricket",
                "f1": "f1",
                "formula-1": "f1",
                "formula1": "f1",
                "motorsport": "f1",
            }
        ),
        (
            {
                "soccer": "soccer",
                "basketball": "basketball",
                "tennis": "tennis",
                "golf": "golf",
            }
        ),
    ]
    generic_sports = {"sports", "all", "football", "baseball", "hockey"}

    for mapping in priority_groups:
        for tag in normalized_tags:
            if tag in mapping:
                return mapping[tag]
    for tag in normalized_tags:
        if tag not in generic_sports:
            return "other_sports"
    return "other_sports"


def is_integer_like(value: float, tolerance: float = 1e-6) -> bool:
    return abs(value - round(value)) < tolerance


def build_execution_profile(frame: pd.DataFrame, portfolio: dict[str, Any]) -> dict[str, Any]:
    # 用户标签不是单一规则，而是把 Maker/Taker、交易频率、事件集中度、
    # 低价买入习惯以及 PnL 状态拼成一个更接近“研究标签”的组合画像。
    integer_mask = frame["size"].map(is_integer_like)
    integer_count = int(integer_mask.sum())
    decimal_count = int((~integer_mask).sum())
    total = int(len(frame))
    integer_ratio = integer_count / total if total else 0.0
    decimal_ratio = decimal_count / total if total else 0.0
    sampled_days = max(frame["trade_day"].nunique(), 1) if "trade_day" in frame.columns else 1
    trades_per_active_day = total / sampled_days if sampled_days else float(total)
    total_notional = float(frame["notional"].sum()) if "notional" in frame.columns else 0.0
    buy_notional = float(frame.loc[frame["side"] == "BUY", "notional"].sum()) if "side" in frame.columns else 0.0
    buy_notional_share = buy_notional / total_notional if total_notional else 0.0
    buy_trades = frame[frame["side"] == "BUY"]
    low_price_buy_share = (
        float((buy_trades["price"] <= 0.25).mean()) if not buy_trades.empty else 0.0
    )

    category_summary = (
        frame.groupby("category_key", dropna=False)["transactionHash"]
        .count()
        .sort_values(ascending=False)
    )
    dominant_category_key = category_summary.index[0] if not category_summary.empty else "other"
    dominant_category_count = int(category_summary.iloc[0]) if not category_summary.empty else 0
    dominant_category_share = dominant_category_count / total if total else 0.0

    sports_frame = frame[frame["category_key"] == "sports"]
    sports_sub_summary = (
        sports_frame.groupby("sports_subcategory_key", dropna=False)["transactionHash"]
        .count()
        .sort_values(ascending=False)
    )
    dominant_sports_key = None
    dominant_sports_count = 0
    dominant_sports_share = 0.0
    if not sports_sub_summary.empty:
        dominant_sports_key = sports_sub_summary.index[0]
        dominant_sports_count = int(sports_sub_summary.iloc[0])
        sports_total = int(sports_sub_summary.sum())
        dominant_sports_share = dominant_sports_count / sports_total if sports_total else 0.0
        if pd.isna(dominant_sports_key):
            dominant_sports_key = None

    if integer_ratio > 0.5:
        tendency = "taker"
    elif decimal_ratio > 0.5:
        tendency = "maker"
    else:
        tendency = "mixed"

    event_summary = (
        frame.groupby("event_label", dropna=False)["transactionHash"]
        .count()
        .sort_values(ascending=False)
    )
    dominant_event_share = (float(event_summary.iloc[0]) / total) if not event_summary.empty and total else 0.0

    if trades_per_active_day >= 150 and tendency in {"maker", "taker"}:
        primary_style_key = f"high_frequency_{tendency}"
    elif low_price_buy_share >= 0.55 and buy_notional_share >= 0.6:
        primary_style_key = "low_price_accumulator"
    elif dominant_event_share >= 0.4:
        primary_style_key = "event_sniper"
    elif buy_notional_share >= 0.78:
        primary_style_key = "conviction_buyer"
    elif 0.35 <= buy_notional_share <= 0.65 and frame["market_title"].nunique() >= 10:
        primary_style_key = "balanced_rotator"
    else:
        primary_style_key = tendency

    secondary_tags: list[str] = []
    if trades_per_active_day >= 150:
        secondary_tags.append("high_frequency")
    if dominant_event_share >= 0.4:
        secondary_tags.append("event_concentrated")
    if low_price_buy_share >= 0.45:
        secondary_tags.append("low_price_buyer")
    if buy_notional_share >= 0.68:
        secondary_tags.append("buy_heavy")
    if portfolio.get("total_pnl", 0.0) > 0:
        secondary_tags.append("profitable")
    elif portfolio.get("total_pnl", 0.0) < 0:
        secondary_tags.append("underwater")

    return {
        "tendency": tendency,
        "primary_style_key": primary_style_key,
        "integer_count": integer_count,
        "decimal_count": decimal_count,
        "integer_ratio": integer_ratio,
        "decimal_ratio": decimal_ratio,
        "dominant_category_key": dominant_category_key,
        "dominant_category_count": dominant_category_count,
        "dominant_category_share": dominant_category_share,
        "dominant_sports_key": dominant_sports_key,
        "dominant_sports_count": dominant_sports_count,
        "dominant_sports_share": dominant_sports_share,
        "trades_per_active_day": trades_per_active_day,
        "low_price_buy_share": low_price_buy_share,
        "dominant_event_share": dominant_event_share,
        "buy_notional_share": buy_notional_share,
        "secondary_tags": secondary_tags,
    }


def validate_address(raw_address: str) -> str:
    address = raw_address.strip()
    if not ADDRESS_PATTERN.fullmatch(address):
        raise ValueError(tr("invalid_address"))
    return address.lower()


def api_get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:300] if response.text else str(exc)
        raise PolymarketAPIError(body, status_code=response.status_code) from exc
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def fetch_user_trades_page(
    address: str, limit: int, offset: int, end: int | None = None
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "user": address,
        "type": "TRADE",
        "limit": min(limit, TRADE_PAGE_LIMIT),
        "offset": max(offset, 0),
        "sortBy": "TIMESTAMP",
        "sortDirection": "DESC",
    }
    if end is not None:
        params["end"] = max(end, 0)
    payload = api_get_json(
        f"{DATA_API}/activity",
        params=params,
    )
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, list):
            return value
    raise PolymarketAPIError("Trades payload format is not recognized.")


def should_retry_trade_fetch(error: Exception) -> bool:
    if isinstance(error, requests.RequestException):
        return True
    if isinstance(error, PolymarketAPIError):
        return error.status_code in RETRYABLE_STATUS_CODES
    return False


def fetch_user_trades_page_with_retry(
    address: str, limit: int, offset: int, end: int | None = None
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(TRADE_FETCH_RETRIES):
        try:
            return fetch_user_trades_page(address=address, limit=limit, offset=offset, end=end)
        except (PolymarketAPIError, requests.RequestException) as exc:
            last_error = exc
            if attempt == TRADE_FETCH_RETRIES - 1 or not should_retry_trade_fetch(exc):
                raise
            backoff_seconds = TRADE_FETCH_BACKOFF_BASE_SECONDS * (2**attempt)
            time.sleep(backoff_seconds)
    if last_error:
        raise last_error
    return []


def build_trade_signature(trade: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(trade.get("transactionHash") or ""),
        str(trade.get("conditionId") or ""),
        str(trade.get("asset") or ""),
        str(trade.get("price") or ""),
        str(trade.get("size") or ""),
        str(trade.get("timestamp") or ""),
        str(trade.get("side") or ""),
        str(trade.get("outcome") or ""),
    )


@st.cache_data(show_spinner=False, ttl=300)
def fetch_user_trades(address: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    capped_limit = max(0, min(limit, DEFAULT_LIMIT))
    if capped_limit == 0:
        return []

    collected: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()
    end_cursor: int | None = None
    history_exhausted = False

    while len(collected) < capped_limit and not history_exhausted:
        offset = 0
        oldest_timestamp_in_window: int | None = None
        window_new_rows = 0

        # 官方 activity 接口存在历史 offset 上限，单纯翻页拿不到 10k。
        # 这里先在当前时间窗口内翻页，再把 end 游标回退到更早时间继续抓。
        while len(collected) < capped_limit and offset <= TRADE_WINDOW_OFFSET_LIMIT:
            remaining = capped_limit - len(collected)
            page_limit = min(TRADE_PAGE_LIMIT, remaining)
            page = fetch_user_trades_page_with_retry(
                address=address,
                limit=page_limit,
                offset=offset,
                end=end_cursor,
            )
            if not page:
                history_exhausted = True
                break

            timestamps = [
                int(timestamp)
                for timestamp in (trade.get("timestamp") for trade in page)
                if timestamp is not None
            ]
            if timestamps:
                page_oldest_timestamp = min(timestamps)
                oldest_timestamp_in_window = (
                    page_oldest_timestamp
                    if oldest_timestamp_in_window is None
                    else min(oldest_timestamp_in_window, page_oldest_timestamp)
                )

            page_new_rows = 0
            for trade in page:
                signature = build_trade_signature(trade)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                collected.append(trade)
                page_new_rows += 1
                if len(collected) >= capped_limit:
                    break

            window_new_rows += page_new_rows
            if len(page) < page_limit:
                history_exhausted = True
                break
            offset += len(page)

        if len(collected) >= capped_limit or history_exhausted:
            break
        if oldest_timestamp_in_window is None or window_new_rows == 0:
            break
        end_cursor = max(oldest_timestamp_in_window - 1, 0)

    return collected


@st.cache_data(show_spinner=False, ttl=300)
def fetch_current_positions_page(address: str, limit: int, offset: int) -> list[dict[str, Any]]:
    payload = api_get_json(
        f"{DATA_API}/positions",
        params={
            "user": address,
            "limit": min(limit, POSITIONS_PAGE_LIMIT),
            "offset": max(offset, 0),
            "sizeThreshold": 0,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        },
    )
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, list):
            return value
    raise PolymarketAPIError("Positions payload format is not recognized.")


def fetch_current_positions_page_with_retry(address: str, limit: int, offset: int) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(TRADE_FETCH_RETRIES):
        try:
            return fetch_current_positions_page(address=address, limit=limit, offset=offset)
        except (PolymarketAPIError, requests.RequestException) as exc:
            last_error = exc
            if attempt == TRADE_FETCH_RETRIES - 1 or not should_retry_trade_fetch(exc):
                raise
            time.sleep(TRADE_FETCH_BACKOFF_BASE_SECONDS * (2**attempt))
    if last_error:
        raise last_error
    return []


def collect_paginated_rows(
    *,
    address: str,
    page_limit: int,
    max_offset: int,
    page_fetcher: Any,
    signature_builder: Any,
) -> list[dict[str, Any]]:
    # positions / closed-positions 都是标准 offset 分页，这里抽成通用收集器。
    # 逻辑上同时处理并发抓取、去重和“短页即结束”判断。
    collected: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()
    offset = 0

    while offset <= max_offset:
        offsets = [current for current in range(offset, max_offset + 1, page_limit)][:POSITIONS_FETCH_BATCHES]
        if not offsets:
            break

        with ThreadPoolExecutor(max_workers=min(len(offsets), POSITIONS_FETCH_BATCHES)) as executor:
            future_map = {
                executor.submit(page_fetcher, address=address, limit=page_limit, offset=current): current
                for current in offsets
            }
            pages = {future_map[future]: future.result() for future in as_completed(future_map)}

        should_stop = False
        for current in sorted(pages):
            page = pages[current]
            if not page:
                should_stop = True
                break

            new_rows = 0
            for row in page:
                signature = signature_builder(row)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                collected.append(row)
                new_rows += 1

            if len(page) < page_limit or new_rows == 0:
                should_stop = True
                break

        if should_stop:
            break
        offset = offsets[-1] + page_limit

    return collected


@st.cache_data(show_spinner=False, ttl=300)
def fetch_current_positions(address: str) -> list[dict[str, Any]]:
    return collect_paginated_rows(
        address=address,
        page_limit=POSITIONS_PAGE_LIMIT,
        max_offset=10_000,
        page_fetcher=fetch_current_positions_page_with_retry,
        signature_builder=lambda row: (
            str(row.get("conditionId") or ""),
            str(row.get("asset") or ""),
            str(row.get("outcome") or ""),
        ),
    )


@st.cache_data(show_spinner=False, ttl=300)
def fetch_closed_positions_page(address: str, limit: int, offset: int) -> list[dict[str, Any]]:
    payload = api_get_json(
        f"{DATA_API}/closed-positions",
        params={
            "user": address,
            "limit": min(limit, CLOSED_POSITIONS_PAGE_LIMIT),
            "offset": max(offset, 0),
        },
    )
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, list):
            return value
    raise PolymarketAPIError("Closed positions payload format is not recognized.")


def fetch_closed_positions_page_with_retry(address: str, limit: int, offset: int) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(TRADE_FETCH_RETRIES):
        try:
            return fetch_closed_positions_page(address=address, limit=limit, offset=offset)
        except (PolymarketAPIError, requests.RequestException) as exc:
            last_error = exc
            if attempt == TRADE_FETCH_RETRIES - 1 or not should_retry_trade_fetch(exc):
                raise
            time.sleep(TRADE_FETCH_BACKOFF_BASE_SECONDS * (2**attempt))
    if last_error:
        raise last_error
    return []


@st.cache_data(show_spinner=False, ttl=300)
def fetch_closed_positions(address: str) -> list[dict[str, Any]]:
    return collect_paginated_rows(
        address=address,
        page_limit=CLOSED_POSITIONS_PAGE_LIMIT,
        max_offset=CLOSED_POSITIONS_MAX_OFFSET,
        page_fetcher=fetch_closed_positions_page_with_retry,
        signature_builder=lambda row: (
            str(row.get("conditionId") or ""),
            str(row.get("asset") or ""),
            str(row.get("outcome") or ""),
            str(row.get("timestamp") or ""),
        ),
    )


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_event_tags(event_slug: str) -> list[dict[str, Any]]:
    payload = api_get_json(f"{GAMMA_API}/events/slug/{event_slug}")
    tags = payload.get("tags") if isinstance(payload, dict) else None
    if isinstance(tags, list):
        return tags
    return []


def build_wallet_context(address: str, frame: pd.DataFrame) -> WalletContext:
    alias_series = frame["display_name"].dropna()
    alias = alias_series.iloc[0] if not alias_series.empty else short_wallet(address)
    profile_series = frame["profile_image"].dropna()
    profile_image = profile_series.iloc[0] if not profile_series.empty else ""
    return WalletContext(address=address, alias=alias, profile_image=profile_image)


def build_trades_dataframe(trades: list[dict[str, Any]]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()

    frame = pd.DataFrame(trades).copy()
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce").fillna(0.0)
    frame["size"] = pd.to_numeric(frame["size"], errors="coerce").fillna(0.0)
    frame["notional"] = frame["price"] * frame["size"]
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True, errors="coerce")
    frame["timestamp_local"] = frame["timestamp_utc"].dt.tz_convert(APP_TZ)
    frame["side"] = frame["side"].fillna("UNKNOWN")
    frame["outcome"] = frame["outcome"].fillna("Unknown")
    frame["proxyWallet"] = frame["proxyWallet"].fillna("")
    frame["profile_image"] = frame["profileImageOptimized"].replace("", pd.NA).fillna(
        frame["profileImage"].replace("", pd.NA)
    )
    frame["display_name"] = (
        frame["pseudonym"]
        .replace("", pd.NA)
        .fillna(frame["name"].replace("", pd.NA))
        .fillna(frame["proxyWallet"].apply(short_wallet))
    )
    frame["event_label"] = frame["eventSlug"].map(slug_to_title).fillna("Unknown Event")
    frame["market_title"] = frame["title"].fillna(frame["slug"]).fillna(frame["conditionId"])
    frame["contract_label"] = frame.apply(
        lambda row: f"{row['market_title']} [{row['outcome']}]",
        axis=1,
    )
    frame["contract_short"] = frame["contract_label"].map(lambda value: truncate_text(str(value), 48))
    frame["event_short"] = frame["event_label"].map(lambda value: truncate_text(str(value), 34))
    frame["weekday"] = pd.Categorical(
        frame["timestamp_local"].dt.day_name(),
        categories=WEEKDAY_ORDER,
        ordered=True,
    )
    frame["hour"] = frame["timestamp_local"].dt.hour
    frame["trade_day"] = frame["timestamp_local"].dt.floor("D")
    frame["date"] = frame["trade_day"].dt.date
    frame["local_time_label"] = frame["timestamp_local"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return frame.sort_values("timestamp_local")


def build_positions_dataframe(positions: list[dict[str, Any]]) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame()

    # 官方持仓接口字段比较偏原始接口口径，先在这里统一数值列和展示列，
    # 后面的 PnL 卡片、持仓图和表格都复用这份标准化后的 DataFrame。
    frame = pd.DataFrame(positions).copy()
    numeric_columns = [
        "size",
        "avgPrice",
        "initialValue",
        "currentValue",
        "cashPnl",
        "percentPnl",
        "totalBought",
        "realizedPnl",
        "percentRealizedPnl",
        "curPrice",
    ]
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        else:
            frame[column] = 0.0

    frame["event_label"] = frame["eventSlug"].map(slug_to_title).fillna("Unknown Event")
    frame["market_title"] = frame["title"].fillna(frame["slug"]).fillna(frame["conditionId"])
    frame["contract_label"] = frame.apply(
        lambda row: f"{row['market_title']} [{row['outcome']}]",
        axis=1,
    )
    frame["contract_short"] = frame["contract_label"].map(lambda value: truncate_text(str(value), 48))
    frame["position_total_pnl"] = frame["cashPnl"] + frame["realizedPnl"]
    frame["end_date"] = pd.to_datetime(frame.get("endDate"), utc=True, errors="coerce")
    frame["end_date_label"] = frame["end_date"].dt.strftime("%Y-%m-%d")
    frame["end_date_label"] = frame["end_date_label"].fillna("—")
    return frame.sort_values("currentValue", ascending=False)


def build_portfolio_snapshot(
    open_positions: pd.DataFrame, closed_positions: pd.DataFrame
) -> dict[str, Any]:
    # 面板上的 PnL 汇总口径：
    # unrealized 来自当前持仓 cashPnl，
    # realized = 已平仓 realizedPnl + 未平仓仓位中已经实现的 realizedPnl。
    open_value = float(open_positions["currentValue"].sum()) if not open_positions.empty else 0.0
    unrealized_pnl = float(open_positions["cashPnl"].sum()) if not open_positions.empty else 0.0
    realized_open = float(open_positions["realizedPnl"].sum()) if not open_positions.empty else 0.0
    realized_closed = float(closed_positions["realizedPnl"].sum()) if not closed_positions.empty else 0.0
    realized_pnl = realized_open + realized_closed
    total_pnl = realized_pnl + unrealized_pnl
    open_cost_basis = float(open_positions["initialValue"].sum()) if not open_positions.empty else 0.0
    return {
        "open_value": open_value,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_pnl": total_pnl,
        "open_cost_basis": open_cost_basis,
        "open_position_count": int(len(open_positions)),
        "closed_position_count": int(len(closed_positions)),
    }


def enrich_event_taxonomy(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    event_slugs = sorted({slug for slug in frame["eventSlug"].dropna().tolist() if str(slug).strip()})
    taxonomy_map: dict[str, dict[str, str | None]] = {}

    with ThreadPoolExecutor(max_workers=MAX_EVENT_FETCH_WORKERS) as executor:
        future_map = {executor.submit(fetch_event_tags, slug): slug for slug in event_slugs}
        for future in as_completed(future_map):
            slug = future_map[future]
            try:
                tags = future.result()
                category_key = derive_primary_category(tags)
                sports_key = derive_sports_subcategory(tags) if category_key == "sports" else None
            except Exception:
                category_key = "other"
                sports_key = None
            taxonomy_map[slug] = {
                "category_key": category_key,
                "sports_subcategory_key": sports_key,
            }

    enriched = frame.copy()
    enriched["category_key"] = enriched["eventSlug"].map(
        lambda slug: taxonomy_map.get(slug, {}).get("category_key", "other")
    )
    enriched["sports_subcategory_key"] = enriched["eventSlug"].map(
        lambda slug: taxonomy_map.get(slug, {}).get("sports_subcategory_key")
    )
    return enriched


def collapse_minor_contracts(frame: pd.DataFrame, top_n: int = 16) -> pd.DataFrame:
    top_contracts = (
        frame.groupby("contract_short", dropna=False)["notional"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .index
    )
    collapsed = frame.copy()
    collapsed["chart_contract"] = collapsed["contract_short"].where(
        collapsed["contract_short"].isin(top_contracts),
        "Other contracts",
    )
    return collapsed


def render_hero(context: WalletContext, frame: pd.DataFrame, requested_limit: int) -> None:
    start_time = frame["timestamp_local"].min()
    end_time = frame["timestamp_local"].max()
    sampled_days = max((end_time - start_time).days, 1)
    chips = [
        short_wallet(context.address),
        tr("chip_recent_trades", count=f"{len(frame):,}"),
        tr("chip_markets", count=frame["market_title"].nunique()),
        tr("chip_events", count=frame["event_label"].nunique()),
        tr("chip_day_sample", count=sampled_days),
    ]
    chip_html = "".join(f'<span class="chip">{html.escape(chip)}</span>' for chip in chips)

    st.markdown(
        f"""
        <section class="hero-shell">
          <div class="hero-copy">
            <div class="eyebrow">{html.escape(tr("hero_eyebrow"))}</div>
            <h1 class="hero-title">{html.escape(context.alias)}</h1>
            <p class="hero-subtitle">
              {html.escape(tr("hero_subtitle", limit=f"{requested_limit:,}"))}
            </p>
            <div class="chip-row">{chip_html}</div>
          </div>
          <div class="hero-panel">
            <div>
              <div class="panel-label">{html.escape(tr("tracked_wallet"))}</div>
              <div class="panel-address">{html.escape(context.address)}</div>
            </div>
            <div>
              <div class="panel-label">{html.escape(tr("sampled_notional"))}</div>
              <div class="panel-stat">{html.escape(format_usd(frame['notional'].sum()))}</div>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(frame: pd.DataFrame) -> None:
    total_notional = frame["notional"].sum()
    sell_notional = frame.loc[frame["side"] == "SELL", "notional"].sum()
    buy_notional = frame.loc[frame["side"] == "BUY", "notional"].sum()
    avg_trade = total_notional / len(frame) if len(frame) else 0
    buy_ratio = buy_notional / total_notional if total_notional else 0
    snapshot_cards = [
        (tr("kpi_recent_trades"), f"{len(frame):,}", tr("kpi_recent_trades_note")),
        (tr("kpi_sampled_notional"), format_usd(total_notional), tr("kpi_sampled_notional_note", value=format_usd(avg_trade))),
        (
            tr("kpi_distinct_markets"),
            format_compact_number(frame["market_title"].nunique()),
            tr("kpi_distinct_markets_note", count=frame["event_label"].nunique()),
        ),
        (tr("kpi_buy_pressure"), f"{buy_ratio:.1%}", tr("kpi_buy_pressure_note", value=format_usd(sell_notional))),
    ]
    columns = st.columns(4)
    for column, (label, value, note) in zip(columns, snapshot_cards, strict=False):
        column.markdown(build_metric_card(label, value, note), unsafe_allow_html=True)


def render_focus_cards(frame: pd.DataFrame) -> None:
    top_contracts = (
        frame.groupby("contract_label", dropna=False)["notional"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )
    if top_contracts.empty:
        return
    st.markdown(f"#### {tr('focus_contracts_heading')}")
    columns = st.columns(len(top_contracts))
    for column, (label, notional) in zip(columns, top_contracts.items(), strict=False):
        trade_count = int(frame.loc[frame["contract_label"] == label, "transactionHash"].count())
        avg_price = frame.loc[frame["contract_label"] == label, "price"].mean()
        column.markdown(
            build_snapshot_card(
                truncate_text(str(label), 28),
                format_usd(notional),
                tr("focus_contracts_note", count=trade_count, price=f"{avg_price:.1%}"),
            ),
            unsafe_allow_html=True,
        )


def build_profile_card(profile: dict[str, Any]) -> str:
    # 这里把结构化画像结果转成前端文案卡片，避免判定逻辑和展示文案混在一起。
    tendency = profile["tendency"]
    category_label = localize_category(profile["dominant_category_key"])
    style_key = profile["primary_style_key"]
    style_label = tr(f"profile_behavior_{style_key}")
    archetype_title = tr("profile_combo_pattern", category=category_label, behavior=style_label)
    title_key = {
        "taker": "profile_title_taker",
        "maker": "profile_title_maker",
        "mixed": "profile_title_mixed",
    }[tendency]
    note_key = {
        "taker": "profile_note_taker",
        "maker": "profile_note_maker",
        "mixed": "profile_note_mixed",
    }[tendency]
    reason_label = tr(f"profile_reason_{style_key}")
    secondary_tags = [tr(f"tag_{tag}") for tag in profile["secondary_tags"]]
    chips = [
        f"{tr('profile_primary_category')}: {category_label}",
        f"{tr('profile_primary_category_share')}: {profile['dominant_category_share']:.1%}",
        f"{tr('profile_integer_share')}: {profile['integer_ratio']:.1%}",
        f"{tr('profile_decimal_share')}: {profile['decimal_ratio']:.1%}",
        f"{tr('profile_integer_count')}: {profile['integer_count']:,}",
        f"{tr('profile_decimal_count')}: {profile['decimal_count']:,}",
        f"{tr('profile_style_trades_per_day')}: {profile['trades_per_active_day']:.1f}",
        f"{tr('profile_style_low_price_buy_share')}: {profile['low_price_buy_share']:.1%}",
        f"{tr('profile_style_top_event_share')}: {profile['dominant_event_share']:.1%}",
    ]
    if profile["dominant_category_key"] == "sports" and profile["dominant_sports_key"]:
        chips.append(
            f"{tr('profile_primary_sport')}: {localize_sports_subcategory(profile['dominant_sports_key'])}"
        )
        chips.append(
            f"{tr('profile_primary_sport_share')}: {profile['dominant_sports_share']:.1%}"
        )
    chip_html = "".join(f'<span class="profile-chip">{html.escape(chip)}</span>' for chip in chips)
    return f"""
    <div class="profile-card">
      <div class="profile-kicker">{html.escape(tr('profile_tag_heading'))}</div>
      <div class="profile-title">{html.escape(archetype_title)}</div>
      <div class="profile-note">{html.escape(tr('profile_style_title'))}: {html.escape(style_label)}</div>
      <div class="profile-note">{html.escape(tr(title_key))}</div>
      <div class="profile-note">{html.escape(tr('profile_style_reason'))}: {html.escape(reason_label)}</div>
      <div class="profile-note">{html.escape(tr(note_key))}</div>
      <div class="profile-note">{html.escape(tr('profile_rule'))}</div>
      {"<div class='profile-note'>" + html.escape(tr('profile_secondary_tags')) + ": " + html.escape(" · ".join(secondary_tags)) + "</div>" if secondary_tags else ""}
      <div class="profile-chip-row">{chip_html}</div>
    </div>
    """


def make_execution_profile_figure(profile: dict[str, Any]) -> go.Figure:
    summary = pd.DataFrame(
        [
            {
                "label": tr("profile_integer_share"),
                "count": profile["integer_count"],
                "color": "#7da8ff",
            },
            {
                "label": tr("profile_decimal_share"),
                "count": profile["decimal_count"],
                "color": "#c9d0da",
            },
        ]
    )
    fig = px.pie(
        summary,
        values="count",
        names="label",
        color="label",
        color_discrete_map={row["label"]: row["color"] for _, row in summary.iterrows()},
        title=tr("profile_chart_title"),
        hole=0.55,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate=f"%{{label}}<br>%{{value}} {tr('table_trades').lower()}<br>%{{percent}}<extra></extra>",
    )
    fig.update_layout(showlegend=False)
    return apply_figure_style(fig, height=380)


def render_execution_profile_section(frame: pd.DataFrame, portfolio: dict[str, Any]) -> None:
    profile = build_execution_profile(frame, portfolio)
    left, right = st.columns([1.05, 0.95])
    left.markdown(build_profile_card(profile), unsafe_allow_html=True)
    right.plotly_chart(make_execution_profile_figure(profile), use_container_width=True, config=PLOTLY_CONFIG)


def render_category_mix_section(frame: pd.DataFrame) -> None:
    category_fig = make_category_mix_figure(frame)
    is_all_sports = frame["category_key"].eq("sports").all()
    has_sports_breakdown = frame["sports_subcategory_key"].notna().any()

    if is_all_sports and has_sports_breakdown:
        left, right = st.columns(2)
        left.plotly_chart(category_fig, use_container_width=True, config=PLOTLY_CONFIG)
        right.plotly_chart(make_sports_mix_figure(frame), use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.plotly_chart(category_fig, use_container_width=True, config=PLOTLY_CONFIG)


def make_positions_value_figure(open_positions: pd.DataFrame) -> go.Figure:
    if open_positions.empty:
        fig = go.Figure()
        fig.update_layout(title=tr("positions_chart_title"))
        return apply_figure_style(fig, height=380)

    plot_frame = (
        open_positions.nlargest(10, "currentValue")[
            ["contract_short", "currentValue", "position_total_pnl", "event_label", "outcome", "curPrice", "avgPrice"]
        ]
        .sort_values("currentValue", ascending=True)
        .copy()
    )
    plot_frame["pnl_direction"] = plot_frame["position_total_pnl"].map(
        lambda value: "positive" if value >= 0 else "negative"
    )
    fig = px.bar(
        plot_frame,
        x="currentValue",
        y="contract_short",
        orientation="h",
        color="pnl_direction",
        color_discrete_map={"positive": "#7da8ff", "negative": "#c9d0da"},
        title=tr("positions_chart_title"),
        labels={
            "currentValue": tr("positions_breakdown_value"),
            "position_total_pnl": tr("positions_breakdown_total"),
            "contract_short": "",
            "event_label": tr("positions_table_event"),
            "outcome": tr("positions_table_outcome"),
            "curPrice": tr("positions_table_cur_price"),
            "avgPrice": tr("positions_table_avg_price"),
        },
        hover_data={
            "event_label": True,
            "outcome": True,
            "avgPrice": ":.3f",
            "curPrice": ":.3f",
            "currentValue": ":,.2f",
            "position_total_pnl": ":,.2f",
            "pnl_direction": False,
        },
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickprefix="$")
    return apply_figure_style(fig, height=380)


def render_positions_table(open_positions: pd.DataFrame) -> None:
    if open_positions.empty:
        st.markdown(
            f"""
            <div class="insight-card">
              <div class="insight-title">{html.escape(tr("positions_current_title"))}</div>
              <div class="insight-copy">{html.escape(tr("positions_empty"))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # 汇总指标使用全量持仓，但表格只展示前 40 个，避免超高频 bot 直接把页面拖慢。
    table = open_positions.head(40)[
        [
            "event_label",
            "market_title",
            "outcome",
            "size",
            "avgPrice",
            "curPrice",
            "initialValue",
            "currentValue",
            "cashPnl",
            "realizedPnl",
            "position_total_pnl",
            "end_date_label",
        ]
    ].copy()
    table["size"] = table["size"].map(lambda value: f"{value:,.2f}")
    table["avgPrice"] = table["avgPrice"].map(lambda value: f"{value:.1%}")
    table["curPrice"] = table["curPrice"].map(lambda value: f"{value:.1%}")
    for column in ("initialValue", "currentValue", "cashPnl", "realizedPnl", "position_total_pnl"):
        formatter = format_signed_usd if "Pnl" in column or column == "position_total_pnl" else format_usd
        table[column] = table[column].map(formatter)
    table = table.rename(
        columns={
            "event_label": tr("positions_table_event"),
            "market_title": tr("positions_table_market"),
            "outcome": tr("positions_table_outcome"),
            "size": tr("positions_table_size"),
            "avgPrice": tr("positions_table_avg_price"),
            "curPrice": tr("positions_table_cur_price"),
            "initialValue": tr("positions_table_cost_basis"),
            "currentValue": tr("positions_table_value"),
            "cashPnl": tr("positions_table_unrealized"),
            "realizedPnl": tr("positions_table_realized"),
            "position_total_pnl": tr("positions_table_total"),
            "end_date_label": tr("positions_table_end_date"),
        }
    )
    st.markdown(f"#### {tr('positions_current_title')}")
    st.caption(tr("positions_table_note"))
    st.dataframe(table, width="stretch", hide_index=True)


def render_positions_section(open_positions: pd.DataFrame, closed_positions: pd.DataFrame) -> dict[str, Any]:
    # 持仓区返回 portfolio 汇总，后面的用户标签会复用总 PnL 结果做次级标签。
    portfolio = build_portfolio_snapshot(open_positions, closed_positions)
    st.markdown(f"#### {tr('positions_heading')}")
    st.markdown(
        f"""
        <div class="insight-card">
          <div class="insight-copy">{html.escape(tr("positions_note"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards = [
        (
            tr("positions_open_value"),
            format_usd(portfolio["open_value"]),
            tr("positions_open_value_note", count=portfolio["open_position_count"]),
        ),
        (
            tr("positions_unrealized_pnl"),
            format_signed_usd(portfolio["unrealized_pnl"]),
            tr("positions_unrealized_pnl_note"),
        ),
        (
            tr("positions_realized_pnl"),
            format_signed_usd(portfolio["realized_pnl"]),
            tr("positions_realized_pnl_note", count=portfolio["closed_position_count"]),
        ),
        (
            tr("positions_total_pnl"),
            format_signed_usd(portfolio["total_pnl"]),
            tr("positions_total_pnl_note"),
        ),
    ]
    card_columns = st.columns(4)
    for column, (label, value, note) in zip(card_columns, cards, strict=False):
        column.markdown(build_metric_card(label, value, note), unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95])
    with left:
        if open_positions.empty:
            st.markdown(
                f"""
                <div class="insight-card">
                  <div class="insight-title">{html.escape(tr("positions_heading"))}</div>
                  <div class="insight-copy">{html.escape(tr("positions_empty"))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.plotly_chart(
                make_positions_value_figure(open_positions),
                use_container_width=True,
                config=PLOTLY_CONFIG,
            )
    with right:
        render_positions_table(open_positions)

    return portfolio


def apply_figure_style(fig: go.Figure, *, height: int = 430) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=44, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(251,251,253,0.92)",
        font=dict(color="#111111", family='-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif'),
        legend_title_text="",
        title=dict(font=dict(size=18, color="#111111"), x=0.03, xanchor="left"),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="rgba(17,17,17,0.08)", font=dict(color="#111111")),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(17, 17, 17, 0.06)", zeroline=False, linecolor="rgba(17,17,17,0.06)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(17, 17, 17, 0.06)", zeroline=False, linecolor="rgba(17,17,17,0.06)")
    return fig


def make_activity_timeline(frame: pd.DataFrame) -> go.Figure:
    side_map = localized_side_map()
    daily = (
        frame.groupby(["trade_day", "side"], dropna=False)
        .agg(notional=("notional", "sum"), trades=("transactionHash", "count"))
        .reset_index()
    )
    daily_total = (
        frame.groupby("trade_day", dropna=False)["transactionHash"]
        .count()
        .reset_index(name="trade_count")
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for side, color in SIDE_COLORS.items():
        side_slice = daily[daily["side"] == side]
        fig.add_trace(
            go.Bar(
                x=side_slice["trade_day"],
                y=side_slice["notional"],
                name=side_map.get(side, side),
                marker_color=color,
                opacity=0.86,
            ),
            secondary_y=False,
        )
    fig.add_trace(
        go.Scatter(
            x=daily_total["trade_day"],
            y=daily_total["trade_count"],
            name=tr("trade_count"),
            mode="lines+markers",
            line=dict(color="#0f2741", width=3),
            marker=dict(size=6),
        ),
        secondary_y=True,
    )
    fig.update_layout(title=tr("activity_timeline_title"), barmode="relative")
    fig.update_yaxes(title_text=tr("activity_timeline_y_left"), tickprefix="$", secondary_y=False)
    fig.update_yaxes(title_text=tr("activity_timeline_y_right"), secondary_y=True)
    return apply_figure_style(fig, height=430)


def make_top_markets_figure(frame: pd.DataFrame) -> go.Figure:
    leaderboard = (
        frame.groupby("contract_short", dropna=False)
        .agg(notional=("notional", "sum"), trades=("transactionHash", "count"))
        .reset_index()
        .sort_values("notional", ascending=False)
        .head(15)
    )
    fig = px.bar(
        leaderboard,
        x="notional",
        y="contract_short",
        orientation="h",
        color="trades",
        color_continuous_scale=["#f7f8fa", "#d9e4fb", "#b7cbf8", "#7da8ff"],
        title=tr("top_contracts_title"),
        labels={
            "notional": tr("top_contracts_x"),
            "contract_short": "",
            "trades": tr("table_trades"),
        },
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    fig.update_xaxes(tickprefix="$")
    return apply_figure_style(fig, height=430)


def make_heatmap_figure(frame: pd.DataFrame) -> go.Figure:
    heatmap = (
        frame.pivot_table(
            index="weekday",
            columns="hour",
            values="transactionHash",
            aggfunc="count",
            fill_value=0,
            observed=False,
        )
        .reindex(WEEKDAY_ORDER)
        .fillna(0)
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap.values,
            x=[f"{hour:02d}:00" for hour in heatmap.columns],
            y=[dict(zip(WEEKDAY_ORDER, WEEKDAY_LABELS.get(get_lang(), WEEKDAY_ORDER))).get(day, day) for day in heatmap.index.tolist()],
            colorscale=[
                [0.0, "#fbfbfd"],
                [0.35, "#edf2fb"],
                [0.7, "#cad9f6"],
                [1.0, "#7da8ff"],
            ],
            hovertemplate=f"%{{y}} %{{x}}<br>{tr('table_trades')}: %{{z}}<extra></extra>",
        )
    )
    fig.update_layout(title=tr("heatmap_title"), xaxis_title="", yaxis_title="")
    return apply_figure_style(fig, height=390)


def make_category_mix_figure(frame: pd.DataFrame) -> go.Figure:
    summary = (
        frame.groupby("category_key", dropna=False)
        .agg(trade_count=("transactionHash", "count"), notional=("notional", "sum"))
        .reset_index()
        .sort_values("trade_count", ascending=False)
    )
    summary["label"] = summary["category_key"].map(localize_category)
    color_map = {localize_category(key): value for key, value in CATEGORY_COLORS.items()}
    fig = px.pie(
        summary,
        values="trade_count",
        names="label",
        color="label",
        color_discrete_map=color_map,
        title=tr("category_mix_title"),
        hole=0.45,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        customdata=summary[["notional"]],
        hovertemplate=(
            "%{label}<br>"
            + f"{tr('table_trades')}: "
            + "%{value}<br>"
            + f"{tr('table_notional')}: "
            + "$%{customdata[0]:,.2f}<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False)
    return apply_figure_style(fig, height=380)


def make_sports_mix_figure(frame: pd.DataFrame) -> go.Figure:
    sports_frame = frame[frame["sports_subcategory_key"].notna()].copy()
    summary = (
        sports_frame.groupby("sports_subcategory_key", dropna=False)
        .agg(trade_count=("transactionHash", "count"), notional=("notional", "sum"))
        .reset_index()
        .sort_values("trade_count", ascending=False)
    )
    summary["label"] = summary["sports_subcategory_key"].map(localize_sports_subcategory)
    color_map = {localize_sports_subcategory(key): value for key, value in SPORTS_COLORS.items()}
    fig = px.pie(
        summary,
        values="trade_count",
        names="label",
        color="label",
        color_discrete_map=color_map,
        title=tr("sports_mix_title"),
        hole=0.45,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        customdata=summary[["notional"]],
        hovertemplate=(
            "%{label}<br>"
            + f"{tr('table_trades')}: "
            + "%{value}<br>"
            + f"{tr('table_notional')}: "
            + "$%{customdata[0]:,.2f}<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False)
    return apply_figure_style(fig, height=380)


def make_trade_tape_figure(frame: pd.DataFrame) -> go.Figure:
    tape = collapse_minor_contracts(frame)
    side_map = localized_side_map()
    tape["bubble_size"] = tape["notional"].clip(lower=1).pow(0.5)
    tape["side_label"] = tape["side"].map(side_map).fillna(tape["side"])
    fig = px.scatter(
        tape,
        x="timestamp_local",
        y="chart_contract",
        size="bubble_size",
        color="side_label",
        color_discrete_map={side_map[key]: value for key, value in SIDE_COLORS.items()},
        hover_name="market_title",
        hover_data={
            "local_time_label": True,
            "event_label": True,
            "outcome": True,
            "price": ":.3f",
            "size": ":,.2f",
            "notional": ":,.2f",
            "chart_contract": False,
            "timestamp_local": False,
            "bubble_size": False,
            "side_label": False,
        },
        title=tr("trade_tape_title"),
        labels={
            "timestamp_local": "",
            "chart_contract": "",
            "local_time_label": tr("table_time"),
            "event_label": tr("table_event"),
            "outcome": tr("table_outcome"),
            "price": tr("table_price"),
            "size": tr("table_size"),
            "notional": tr("table_notional"),
            "market_title": tr("table_market"),
        },
        render_mode="webgl",
    )
    fig.update_traces(marker={"opacity": 0.72, "line": {"width": 0}})
    return apply_figure_style(fig, height=520)


def make_price_distribution_figure(frame: pd.DataFrame) -> go.Figure:
    side_map = localized_side_map()
    plot_frame = frame.copy()
    plot_frame["side_label"] = plot_frame["side"].map(side_map).fillna(plot_frame["side"])
    fig = px.histogram(
        plot_frame,
        x="price",
        color="side_label",
        nbins=30,
        opacity=0.76,
        marginal="box",
        color_discrete_map={side_map[key]: value for key, value in SIDE_COLORS.items()},
        title=tr("price_distribution_title"),
        labels={"price": tr("price_label"), "count": tr("trades_label")},
    )
    fig.update_xaxes(tickformat=".0%", range=[0, 1])
    return apply_figure_style(fig, height=420)


def render_market_table(frame: pd.DataFrame) -> None:
    summary = (
        frame.groupby(["contract_label", "event_label"], dropna=False)
        .agg(
            trades=("transactionHash", "count"),
            notional=("notional", "sum"),
            avg_price=("price", "mean"),
            first_seen=("timestamp_local", "min"),
            last_seen=("timestamp_local", "max"),
        )
        .reset_index()
        .sort_values("notional", ascending=False)
        .head(18)
    )
    summary["notional"] = summary["notional"].map(lambda value: f"${value:,.2f}")
    summary["avg_price"] = summary["avg_price"].map(lambda value: f"{value:.1%}")
    summary["first_seen"] = summary["first_seen"].dt.strftime("%Y-%m-%d %H:%M")
    summary["last_seen"] = summary["last_seen"].dt.strftime("%Y-%m-%d %H:%M")
    summary = summary.rename(
        columns={
            "contract_label": tr("table_contract"),
            "event_label": tr("table_event"),
            "trades": tr("table_trades"),
            "notional": tr("table_notional"),
            "avg_price": tr("table_avg_price"),
            "first_seen": tr("table_first_seen"),
            "last_seen": tr("table_last_seen"),
        }
    )
    st.dataframe(summary, width="stretch", hide_index=True)


def render_recent_trades(frame: pd.DataFrame) -> None:
    recent = frame.sort_values("timestamp_local", ascending=False).head(25)[
        [
            "local_time_label",
            "market_title",
            "event_label",
            "side",
            "outcome",
            "price",
            "size",
            "notional",
            "transactionHash",
        ]
    ].copy()
    recent["side"] = recent["side"].map(localized_side_map()).fillna(recent["side"])
    recent["price"] = recent["price"].map(lambda value: f"{value:.1%}")
    recent["size"] = recent["size"].map(lambda value: f"{value:,.2f}")
    recent["notional"] = recent["notional"].map(lambda value: f"${value:,.2f}")
    recent["transactionHash"] = recent["transactionHash"].map(lambda value: short_wallet(str(value)))
    recent = recent.rename(
        columns={
            "local_time_label": tr("table_time"),
            "market_title": tr("table_market"),
            "event_label": tr("table_event"),
            "side": tr("table_side"),
            "outcome": tr("table_outcome"),
            "price": tr("table_price"),
            "size": tr("table_size"),
            "notional": tr("table_notional"),
            "transactionHash": tr("table_tx_hash"),
        }
    )
    st.dataframe(recent, width="stretch", hide_index=True)


def render_price_distribution_explainer(frame: pd.DataFrame) -> None:
    median = frame["price"].median()
    q1 = frame["price"].quantile(0.25)
    q3 = frame["price"].quantile(0.75)
    low = frame["price"].min()
    high = frame["price"].max()
    st.markdown(
        f"""
        <div class="insight-card">
          <div class="insight-title">{html.escape(tr("price_distribution_help_title"))}</div>
          <div class="insight-copy">{html.escape(tr("price_distribution_help_body"))}</div>
          <div class="insight-copy">{html.escape(tr("price_distribution_help_stats", median=f"{median:.1%}", q1=f"{q1:.1%}", q3=f"{q3:.1%}", low=f"{low:.1%}", high=f"{high:.1%}"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filters_section(frame: pd.DataFrame) -> pd.DataFrame:
    with st.expander(tr("filters"), expanded=True):
        side_options = sorted(frame["side"].dropna().unique().tolist())
        event_options = frame["event_label"].dropna().unique().tolist()
        side_map = localized_side_map()
        reverse_side_map = {side_map.get(option, option): option for option in side_options}
        localized_side_options = list(reverse_side_map.keys())
        market_query = st.text_input(tr("market_search"), value="", placeholder=tr("market_search_placeholder"))
        selected_side_labels = st.multiselect(tr("side_filter"), options=localized_side_options, default=localized_side_options)
        selected_sides = [reverse_side_map[label] for label in selected_side_labels]
        selected_events = st.multiselect(tr("events_filter"), options=event_options, default=event_options)
        min_notional = st.slider(
            tr("minimum_notional"),
            min_value=0.0,
            max_value=max(float(frame["notional"].max()), 1.0),
            value=0.0,
            step=max(float(frame["notional"].max()) / 200, 1.0),
        )
        date_min = frame["date"].min()
        date_max = frame["date"].max()
        selected_dates = st.date_input(tr("date_range"), value=(date_min, date_max), min_value=date_min, max_value=date_max)

    filtered = frame[
        frame["side"].isin(selected_sides)
        & frame["event_label"].isin(selected_events)
        & (frame["notional"] >= min_notional)
    ]
    if isinstance(selected_dates, tuple) or isinstance(selected_dates, list):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
            filtered = filtered[(filtered["date"] >= start_date) & (filtered["date"] <= end_date)]
    if market_query.strip():
        filtered = filtered[
            filtered["market_title"].str.contains(market_query.strip(), case=False, na=False)
        ]
    return filtered


def raw_data_section(frame: pd.DataFrame) -> None:
    export = frame[
        [
            "local_time_label",
            "event_label",
            "market_title",
            "side",
            "outcome",
            "price",
            "size",
            "notional",
            "transactionHash",
            "conditionId",
        ]
    ].copy()
    export["side"] = export["side"].map(localized_side_map()).fillna(export["side"])
    export = export.rename(
        columns={
            "local_time_label": tr("table_time"),
            "event_label": tr("table_event"),
            "market_title": tr("table_market"),
            "side": tr("table_side"),
            "outcome": tr("table_outcome"),
            "price": tr("table_price"),
            "size": tr("table_size"),
            "notional": tr("table_notional"),
            "transactionHash": tr("table_tx_hash"),
            "conditionId": tr("table_condition_id"),
        }
    )
    st.dataframe(export, width="stretch", hide_index=True)
    csv_data = export.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        tr("download_csv"),
        data=csv_data,
        file_name="polymarket_wallet_trades.csv",
        mime="text/csv",
    )


def intro_section(selected_limit: int) -> None:
    st.markdown(f"### {tr('scope_heading')}")
    st.markdown(tr("scope_body", limit=f"{selected_limit:,}"))


def main() -> None:
    inject_styles()
    render_language_switcher()
    st.title(tr("app_title"))
    if "trade_limit" not in st.session_state:
        st.session_state["trade_limit"] = DEFAULT_FETCH_SIZE
    selected_limit = int(st.session_state["trade_limit"])
    intro_section(selected_limit)

    default_address = st.session_state.get(
        "wallet_input",
        "0x56687bf447db6ffa42ffe2204a05edaa20f55839",
    )
    input_col, size_col, button_col = st.columns([5, 2, 1])
    with input_col:
        raw_address = st.text_input(
            tr("wallet_input_label"),
            value=default_address,
            placeholder="0x...",
            help=tr("wallet_input_help", limit=f"{selected_limit:,}"),
            key="wallet_input",
        )
    with size_col:
        selected_limit = st.radio(
            tr("fetch_limit_label"),
            options=list(FETCH_LIMIT_OPTIONS),
            horizontal=True,
            help=tr("fetch_limit_help"),
            key="trade_limit",
            format_func=lambda value: f"{value:,}",
        )
    with button_col:
        st.write("")
        st.write("")
        load_clicked = st.button(tr("load_button"), width="stretch")

    if not raw_address and not load_clicked:
        st.stop()
    if not load_clicked and "loaded_frame" not in st.session_state:
        st.stop()

    if load_clicked:
        try:
            with st.spinner(tr("fetch_spinner", limit=f"{selected_limit:,}")):
                address = validate_address(raw_address)
                # 一次加载交易、当前持仓、已平仓结果和事件标签。
                # 这样前端展示时不需要再做二次网络请求，交互更稳定。
                trades = fetch_user_trades(address, limit=selected_limit)
                open_positions = build_positions_dataframe(fetch_current_positions(address))
                closed_positions = build_positions_dataframe(fetch_closed_positions(address))
                frame = build_trades_dataframe(trades)
                frame = enrich_event_taxonomy(frame)
                context = build_wallet_context(address, frame) if not frame.empty else WalletContext(address, short_wallet(address), "")
            st.session_state["loaded_frame"] = frame
            st.session_state["loaded_context"] = context
            st.session_state["loaded_open_positions"] = open_positions
            st.session_state["loaded_closed_positions"] = closed_positions
            st.session_state["loaded_limit"] = selected_limit
        except (ValueError, PolymarketAPIError, requests.RequestException) as exc:
            st.error(tr("fetch_failed", error=str(exc)))
            st.stop()

    frame: pd.DataFrame = st.session_state["loaded_frame"]
    context: WalletContext = st.session_state["loaded_context"]
    open_positions: pd.DataFrame = st.session_state.get("loaded_open_positions", pd.DataFrame())
    closed_positions: pd.DataFrame = st.session_state.get("loaded_closed_positions", pd.DataFrame())
    loaded_limit = int(st.session_state.get("loaded_limit", selected_limit))
    if "category_key" not in frame.columns or "sports_subcategory_key" not in frame.columns:
        frame = enrich_event_taxonomy(frame)
        st.session_state["loaded_frame"] = frame
    if frame.empty:
        st.warning(tr("empty_wallet"))
        st.stop()

    render_hero(context, frame, loaded_limit)
    render_kpis(frame)
    portfolio = render_positions_section(open_positions, closed_positions)
    render_execution_profile_section(frame, portfolio)
    render_focus_cards(frame)
    render_category_mix_section(frame)

    filtered = filters_section(frame)
    if filtered.empty:
        st.warning(tr("empty_filters"))
        st.stop()

    overview_tab, tape_tab, raw_tab = st.tabs([tr("tab_overview"), tr("tab_tape"), tr("tab_raw")])
    with overview_tab:
        left, right = st.columns([1.35, 1])
        left.plotly_chart(make_activity_timeline(filtered), use_container_width=True, config=PLOTLY_CONFIG)
        right.plotly_chart(make_top_markets_figure(filtered), use_container_width=True, config=PLOTLY_CONFIG)
        st.plotly_chart(make_heatmap_figure(filtered), use_container_width=True, config=PLOTLY_CONFIG)
        st.markdown(f"#### {tr('most_active_contracts')}")
        render_market_table(filtered)

    with tape_tab:
        st.plotly_chart(make_trade_tape_figure(filtered), use_container_width=True, config=PLOTLY_CONFIG)
        dist_col, recent_col = st.columns([1.15, 0.85])
        with dist_col:
            render_price_distribution_explainer(filtered)
            st.plotly_chart(make_price_distribution_figure(filtered), use_container_width=True, config=PLOTLY_CONFIG)
        with recent_col:
            st.markdown(f"#### {tr('latest_trades')}")
            render_recent_trades(filtered)

    with raw_tab:
        st.markdown(f"#### {tr('raw_trades')}")
        raw_data_section(filtered)

    source_links = [
        "[API introduction](https://docs.polymarket.com/api-reference/introduction)",
        "[Get user activity](https://docs.polymarket.com/api-reference/core/get-user-activity)",
        "[Get current positions for a user](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)",
        "[Get closed positions for a user](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user)",
        "[Get event by slug](https://docs.polymarket.com/api-reference/events/get-event-by-slug)",
    ]
    st.caption(f"{tr('sources')}: " + " | ".join(source_links))


if __name__ == "__main__":
    main()
