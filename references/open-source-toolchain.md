# 开源工具链选型与接入（open-source-toolchain）

> 何时读：用户问「用什么开源库取数 / 算指标 / 做组合优化」，或需要把本 Skill 的判断接到可复现的数据管线上。本文件只做**选型与边界**，不复刻实现。
>
> 核对时点：2026-11-11（许可证经 GitHub API + 仓库 LICENSE / README 原文交叉核对）。开源项目变动快，引用前按第 6 节复核。

## 1. 三条使用原则

1. **只借事实与接口名，不复制代码**：本 Skill 不 vendor 任何第三方实现；需要时指导用户自行安装、自行运行，输出里标注「用户环境中的开源工具」。
2. **许可证先看再碰**：MIT / Apache-2.0 / BSD-3-Clause 可用于方法论与接口参考；GPL-3.0 不引入代码；无许可证仓库一律排除。**许可证以仓库当前 LICENSE 原文为准**，早期公告、第三方转述、GitHub API 的 `NOASSERTION` 都不能当依据（2026-11-11 核查：OpenBB 当前为 Apache-2.0，非早期流传的 AGPL）。
3. **不默认安装**：本 Skill 的脚本仍是纯标准库。用户没装、环境没网时，回落到 `references/data-sources.md` 的检索路由，不得假装已取到数。

## 2. 按任务选工具

### 2.1 行情、基金与财报数据

| 任务 | 项目 | 许可证 | 能做什么 | 入口 | 风险与边界 |
|---|---|---|---|---|---|
| A 股 / ETF / 基金 / 宏观 | [AKShare](https://github.com/akfamily/akshare) | MIT | 覆盖面最广的境内财经数据接口库，含 ETF 现货、历史净值、指数估值、基金档案 | `pip install akshare`，Python 调用 | 接口多、字段随网页改版易变；**每个数仍要回溯到交易所 / 基金公司原始页** |
| 把 AKShare 暴露成 HTTP / MCP | [aktools](https://github.com/akfamily/aktools) | MIT | AKShare 官方的 HTTP API 与 MCP server（`search_interfaces` / `describe_interface` / `get_data` 三个工具） | MCP：`uvx --from aktools aktools-mcp`（无需预装）；HTTP：`pip install aktools && python -m aktools` | 自建服务，需自己承担可用性与限频；WorkBuddy 可写入用户级 `~/.workbuddy/mcp.json`，配置以运行时上游 README 为准 |
| 自托管 A 股数据湖 | [CNEquity](https://github.com/rootSunc/CNEquity) | Apache-2.0 | 86 个数据集（78 curated + 8 derived），复权、历史成分、PIT、行级溯源，MCP 原生 | 自托管，见仓库 README | 项目较新（2026 年），先小样本验证再依赖 |
| 港股 / 美股 / 全球行情 | [yfinance](https://github.com/ranaroussi/yfinance) | Apache-2.0 | Yahoo Finance 的非官方封装，日线、复权、财报日历 | `pip install yfinance` | 非官方、可能限频或改结构；**不能当一手来源** |
| 美股财报与公告 | [edgartools](https://github.com/dgunning/edgartools) | MIT | SEC EDGAR 的 10-K / 10-Q / 8-K、XBRL 财务、13F、Form 4 | `pip install edgartools` | 需按 SEC 要求设置 User-Agent；只覆盖美股 |
| 财务比率与估值拆解 | [FinanceToolkit](https://github.com/JerBouma/FinanceToolkit) | MIT | 200+ 比率的透明实现，含估值、杜邦、成长性 | `pip install financetoolkit` | 输入数据质量决定结论；默认数据源需另行确认 |

### 2.2 组合、绩效与优化

| 任务 | 项目 | 许可证 | 能做什么 | 边界 |
|---|---|---|---|---|
| 回撤 / 夏普 / 绩效归因 | [quantstats](https://github.com/ranaroussi/quantstats) | Apache-2.0 | 单序列绩效报告、水下曲线、滚动指标 | 只做计算，不含数据；历史表现不预示未来 |
| 组合优化（均值方差 / HRP / CVaR） | [Riskfolio-Lib](https://github.com/dcajasn/Riskfolio-Lib) | BSD-3-Clause | 20+ 风险度量、HRP、风险预算、有效前沿 | 优化结果对协方差估计极敏感，样本不足时不要用 |
| 经典有效前沿 / Black-Litterman | [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) | MIT | 有效前沿、HRP、BL、离散配置 | 同上；观点输入必须来自用户，不得代填 |

### 2.3 平台与回测（本 Skill 不接）

| 项目 | 许可证 | 结论 |
|---|---|---|
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | **Apache-2.0**（2026-11-11 核查 main 分支 LICENSE 首句与 README「3. License」） | 明确排除：定位是重量级数据平台，本 Skill 只做配置与纪律，不接入平台、不引入其代码。该仓库已 301 迁移，GitHub API `license.spdx_id` 返回 `NOASSERTION`（因 LICENSE 首行含自定义版权声明），**不得据此猜测许可证** |
| [backtrader](https://github.com/mementum/backtrader) | GPL-3.0（2024-08 后未更新） | 明确排除：本 Skill 不做择时与策略回测，也不引入 GPL 代码 |

> 本 Skill 的定位是「配置与纪律」，不是「策略研发」。用户要回测，说明边界后建议其自建，不在本 Skill 内输出策略绩效。

## 3. MCP 服务器清单

数据路由第 1 层是「用户已连接的金融类 MCP」。可用的公开实现：

| MCP server | 许可证 | 覆盖 | 备注 |
|---|---|---|---|
| aktools | MIT | A 股 / 基金 / 宏观，AKShare 全量接口 | 自建，最贴合本 Skill 的 A 股主线；上游 README 给出 WorkBuddy 配置方式 `uvx --from aktools aktools-mcp`，首次启动需下载约 150 MB 依赖 |
| CNEquity | Apache-2.0 | A 股数据湖，PIT 与复权内置 | 自建，数据量大，适合批量复现 |
| [financial-datasets/mcp-server](https://github.com/financial-datasets/mcp-server) | MIT | 美股行情与财报 | 需要 `FINANCIAL_DATASETS_API_KEY`（商业 API key）；仓库 2025-06 后未更新，视为低维护 |
| OpenBB MCP | Apache-2.0 | 多资产 | 重量级平台，本 Skill 不接入；如需使用自行评估部署与维护成本 |

**接入判断顺序**：用户已装 MCP → 直接调用；没有 MCP 但本机有 Python → 建议装 AKShare / yfinance 并导出 CSV；两者都没有 → 走 `domain_search` / `WebSearch`，并在研报里说明「未使用本地数据」。任何情况下都不得假设用户已装某个库，也不得把「文档中列出」当作「环境中可用」。

## 4. 与本 Skill 脚本的分工

| 需求 | 用什么 | 说明 |
|---|---|---|
| 单只标的现价快照 | `scripts/quote_probe.py` | 内置腾讯 / 新浪公开端点，支持 A 股、港股、美股，零依赖 |
| 历史净值、成分、规模 | 开源库或一手披露 | 本 Skill 不内置历史行情 |
| 财务比率、估值分位 | `scripts/metrics_calc.py` + 用户数据 | 只对输入值做确定性计算 |
| 组合权重、HHI、再平衡偏离 | `scripts/metrics_calc.py` | 同上 |
| 组合优化、回测 | 用户自建（Riskfolio / PyPortfolioOpt） | 输出仅作参考，不进本 Skill 结论 |

## 5. 数据落地的合规动作

- 用开源库取到的数，仍按 `references/data-sources.md` 记录：`provider` 写「AKShare 1.x（用户环境）」这类**版本 + 来源**，`source_url` 尽量回溯到原始页面。
- 开源库的字段名不等于披露口径：`pe` 可能指静态、TTM 或扣非，必须回到定义。
- 用户自行安装的库版本要记录（`akshare.__version__`），否则无法复现。
- 第三方库的结论（如 quantstats 的夏普）不得直接当「事实」，标为「计算」。

## 6. 复核清单（每季度一次）

- [ ] 许可证是否变更（以仓库当前 LICENSE 原文为准；重点：曾变更过许可证的项目、项目转闭源或换 license）
- [ ] 最近一次提交是否超过 12 个月（超过则降级为「低维护」）
- [ ] 接口是否改版（AKShare / yfinance 高发）
- [ ] 主要数据源是否新增官方 API（优先官方）
- [ ] 本文件表格中的版本、入口、风险描述是否需要更新

复核结果写回本文件的「核对时点」，并在 `CHANGELOG.md` 记一条。

**核查口径**：GitHub REST API `/repos/{owner}/{repo}` 的 `license.spdx_id` 只作线索；返回 `NOASSERTION` / `null` 或仓库发生 301 迁移时，必须回读 LICENSE 与 README 原文。2026-11-11 本次核查中，OpenBB 即属此类：API 为 `NOASSERTION`，LICENSE 首句为「All files in this repository are licensed under the Apache License, Version 2.0」。

## 7. 引用与署名

本文件只引用项目的名称、许可证、公开接口与能力描述，**未复制任何实现代码**。许可证全文与署名规则见 `THIRD_PARTY_NOTICES.md`；如未来需要引入代码，必须先满足该文件的许可证要求并补充对应全文。
