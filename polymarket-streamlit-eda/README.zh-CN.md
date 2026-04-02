# Polymarket Wallet Insight

[English](./README.md)

这是一个面向 Polymarket 单钱包分析的双语 Streamlit 面板。  
输入一个钱包地址后，系统会把它转成一个研究视图，集中展示交易流 EDA、当前持仓、PnL 和行为画像标签。

## 项目能力

- 输入一个 Polymarket 钱包地址
- 选择抓取规模：`1000 / 3000 / 5000 / 10000`
- 通过官方 Polymarket Data API 拉取该钱包的近期交易活动
- 通过官方事件接口补齐 event tags
- 展示当前持仓、已实现 PnL、未实现 PnL、总 PnL
- 生成组合型用户标签，例如 `体育高频 Maker`、`政治事件狙击型`
- 支持导出筛选后的原始交易 CSV

## 核心特性

- 以钱包为中心的交易流分析面板
- 中英双语界面：English / 简体中文
- 针对高频钱包支持最多 `10,000` 笔交易的时间窗口分页抓取
- Apple-inspired 的克制型前端风格，支持响应式布局
- 交易大类分布与体育子类分布饼图
- 活跃时间线、热力图、交易流气泡图、价格分布图
- 基于官方 `positions` 与 `closed-positions` 接口的持仓与 PnL 面板
- 基于执行风格、集中度、低价买入行为与 PnL 状态的用户画像标签

## 官方数据源

本项目使用以下官方 Polymarket API：

- [API introduction](https://docs.polymarket.com/api-reference/introduction)
- [Get user activity](https://docs.polymarket.com/api-reference/core/get-user-activity)
- [Get current positions for a user](https://docs.polymarket.com/api-reference/core/get-current-positions-for-a-user)
- [Get closed positions for a user](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user)
- [Get event by slug](https://docs.polymarket.com/api-reference/events/get-event-by-slug)

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

启动后打开终端中显示的本地 Streamlit 地址即可。

## 推荐抓取规模

- `5000` 适合作为默认值，速度和信息量更平衡
- `10000` 更适合做深度分析
- 对极高频 bot，首次加载会更慢，因为系统还会同时拉取持仓与已平仓数据

## 项目结构

```text
app.py              Streamlit 主程序
README.md           英文说明
README.zh-CN.md     中文说明
.streamlit/         Streamlit 主题配置
```

## 说明

- 当前使用的公开 Polymarket 接口无需额外 API Key
- 对超活跃钱包，冷启动速度会慢于命中缓存后的再次加载
- PnL 使用官方 positions 系列接口口径，而不是只根据当前抓取到的交易样本自行重建
