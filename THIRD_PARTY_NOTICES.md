# 第三方来源、许可证与署名声明

本 Skill（`personal-investing-copilot`）以自建的「现金理财 → 场内 ETF 配置」起步路径为主体，合规吸收了以下开源项目的方法论与少量代码结构。本文件用于说明**每个上游用了什么、以什么许可证使用、做了哪些修改、以及哪些上游被明确排除**。

核查日期：2026-11-10（通过 GitHub REST API `/repos/{owner}/{repo}` 与各仓库内 LICENSE / README 原文核对，非依赖记忆）。Star 数会变动，故不作为依据记录。

**本 Skill 自身**：除下列第三方部分外的文档与代码，自 v1.2.2 起以 **Apache License 2.0** 对外授权，全文见根目录 `LICENSE`，版权与第三方归属声明见根目录 `NOTICE`。`licenses/` 中的文件仅用于覆盖所引用的第三方部分，不代表对本 Skill 整体的授权声明。下游分发必须同时保留 `LICENSE`、`NOTICE`、本文件与 `licenses/` 全部文件，并遵守 Apache-2.0 第 4 条（标注修改、保留归属、不暗示背书）。

## 一、总览

| 上游项目 | 许可证 | 引用类型 | 本 Skill 中对应位置 | 许可证全文 |
|---|---|---|---|---|
| `kidulthhh-dotcom/china-stock-fund-analysis-skill` | Apache-2.0（仓库含 LICENSE + NOTICE.md） | **代码改编** + 方法论改编 | `scripts/data_envelope.py`、`scripts/self_test.py`（结构借鉴）、`references/data-sources.md`、`references/beginner-explainer.md`、`references/release-gates.md`、`references/output-templates.md` 输出契约 | `licenses/Apache-2.0.txt`，上游 NOTICE 见 `licenses/NOTICE-upstream.txt` |
| `abnerk1/anchor-and-tilt` | MIT（Copyright (c) 2026 Abner Araujo） | 方法论参考，重新撰写 | `references/etf-screening.md` 量化对比打分、`references/release-gates.md` 确定性规则与红旗校验 | `licenses/MIT-anchor-and-tilt.txt` |
| `himself65/finance-skills` | MIT（Copyright (c) 2025 Alex Yang） | 方法论参考，重新撰写 | `references/etf-screening.md` 折溢价口径、`references/financial-statement-review.md` 财报点评维度 | `licenses/MIT-finance-skills.txt` |
| `tradermonty/claude-trading-skills` | MIT（Copyright (c) 2026 TraderMonty） | 方法论参考，重新撰写 | `references/release-gates.md` 数据质量五类检查与 PASS / NEED_REVIEW / BLOCK 门控 | `licenses/MIT-claude-trading-skills.txt` |
| `asfamilybank/stock-query` | **README 与 SKILL.md frontmatter 声明 MIT，但 GitHub API `license` 为 `null` 且仓库无 LICENSE 文件** | **仅采用事实性信息，未复制任何实现代码** | `references/data-sources.md` 公开端点域名清单、A 股/ETF 代码位数规则；`scripts/quote_probe.py` 的端点事实 | 上游未提供全文，故不复制代码；说明见下文第二节第 5 项 |
| `anthropics/financial-services` | Apache-2.0 | 未使用代码；仅概念沿袭 | 通过上游 `NOTICE.md` 体现，原文保留在 `licenses/NOTICE-upstream.txt` | 未分发其代码 |

## 二、逐项说明

### 1. kidulthhh-dotcom/china-stock-fund-analysis-skill（Apache-2.0）

仓库：<https://github.com/kidulthhh-dotcom/china-stock-fund-analysis-skill>

**改编的代码**：`scripts/data_envelope.py` 的数据血缘契约（`SourceRef` / `ProviderAttempt` / `DataEnvelope` / `QualityFlag` / `stable_hash` / `normalize_cn_symbol`）改编自该仓库 `china-stock-fund-analysis/scripts/cn_finance/contracts.py`。修改包括：改写为中文文档与中文注释、扩展 `request` 中的交易状态/复权/单位字段约定、调整 `schema_version`、加入本 Skill 的质量标记与告警约定、简化为仅标准库单文件模块。文件头部保留了原始出处、许可证与修改说明。

`scripts/self_test.py` 结构性借鉴该仓库 `scripts/validate_skill.py` 的「依赖无关冒烟检查 + 临时 fixture + JSON 结果 + 快速失败」思路，实现为针对本 Skill 脚本与文档的独立重写，未复制其业务校验代码。

**改编的文档**：`references/data-sources.md` 改编自其 `references/数据源注册表.md`、`references/data-sources.md` 的输出契约与质量门槛；`references/beginner-explainer.md` 改编自其 `references/投资小白解释层.md`。均为中文重新组织、按本 Skill 的「起步配置」主线裁剪，**未逐字复制原文**，并按 Apache-2.0 第 4 条要求保留许可证全文、保留 NOTICE、标注修改、不暗示原作者背书。

该仓库 NOTICE.md 声明其概念与工作流改编自 `anthropics/financial-services`，因此该上游声明一并保留在 `licenses/NOTICE-upstream.txt`。本 Skill 未使用 Anthropic 官方插件的机构级数据连接器、美股口径模型或其任何代码。

### 2. abnerk1/anchor-and-tilt（MIT）

仓库：<https://github.com/abnerk1/anchor-and-tilt>

参考其「给定相同输入应得到相同输出」「缺失信息必须显式声明假设而非静默编数」「交付前红旗校验」的工程纪律，以及 ETF 横向对比的 League Table（逐项打分、按权重决胜）思路。**未采用其美股基金池、具体比例、Vanguard 基准比较等任何数值或标的**。相关规则用中文重新撰写，并改写为 A 股场内 / 起步阶段适用版本。

### 3. himself65/finance-skills（MIT）

仓库：<https://github.com/himself65/finance-skills>

参考 `etf-premium` 中「市价相对 NAV 的折溢价、高溢价买入等于额外付费、跨境/债券/商品类更易出现显著折溢价」的口径说明，以及 `earnings-recap` 的财报点评维度。**未使用其 yfinance 代码、美股标的与第三方 API 依赖**。

### 4. tradermonty/claude-trading-skills（MIT）

仓库：<https://github.com/tradermonty/claude-trading-skills>

参考 `data-quality-checker` 的五类数据质检维度（价格量级、代码/ notation、日期与星期、比例合计、单位口径）与「告警不阻断、供人工复核」的定位，以及 `pre-trade-discipline-gate` 的 `GO / REVIEW_REQUIRED / NO_GO` 分级思路，改写为本 Skill 的 `PASS / NEED_REVIEW / BLOCK` 输出前质检门。**未使用其交易脚本、美股纪律参数与任何 API 密钥逻辑**。

### 5. asfamilybank/stock-query（许可证声明不完整，仅取事实）

仓库：<https://github.com/asfamilybank/stock-query>

该仓库 README 末尾写有 `## License → MIT`，`SKILL.md` frontmatter 写有 `license: MIT`，但 GitHub API 的 `license` 字段为 `null`，仓库内也没有 LICENSE 文件，缺少可核验的许可证全文与版权声明行。基于这一不确定性，本 Skill 采取保守处理：

- **只采用不受著作权保护的事实性信息**：公开行情端点域名（`qt.gtimg.cn`、`hq.sinajs.cn` 等）、A 股 6 位 / 港股 5 位 / 美股 ticker 的代码位数规则、红涨绿跌的 A 股显示惯例、公开接口可能限频与 QDII 净值延迟等已知限制。
- **未复制其 `scripts/sq.sh`、`scripts/fmt.sh` 或任何一行实现代码**。`scripts/quote_probe.py` 为标准库独立实现，两者在解析策略、字段选择、输出结构上均不同。
- 若后续该仓库补齐 LICENSE 全文，可重新评估是否引入其实现；在此之前不得把其代码并入本 Skill。

### 6. 明确排除的上游

- `xticktop/skills`：GitHub API `license` 为 `null`、无 LICENSE 文件，**未使用任何内容**。
- `anthropics/financial-services`：机构级、美股口径、依赖付费数据连接器，与个人投资者起步路径不匹配，**未使用其代码或模型**。
- 其余调研过的仓库（`RKiding/Awesome-finance-skills`、`Xiaoyuan-Liu/national-team-position`、`jangviktor-web/a-stock-data-quant`、`MattStockton/portfolio-analysis` 等）**均未引入代码或文档内容**。

## 三、合规动作清单

- [x] Apache-2.0 上游的 LICENSE 全文随包分发（`licenses/Apache-2.0.txt`）。
- [x] Apache-2.0 上游的 NOTICE 原文随包分发（`licenses/NOTICE-upstream.txt`），保留其对 Anthropic 上游的声明链。
- [x] 所有 MIT 上游的 LICENSE 全文（含版权声明行）随包分发于 `licenses/`。
- [x] 改编的源文件头部标注原作者/仓库/许可证/修改说明。
- [x] 未声称任何上游作者为本 Skill 背书或参与维护。
- [x] 许可证声明不完整或无许可证的项目，不引入实现代码。
- [x] 本 Skill 的行情端点均为公开非登录接口，脚本仅发送标的代码，不发送持仓、账户或任何个人数据；端点可用性、字段含义与调用频率限制均要求运行时核实。
- [x] 本 Skill 自身的 `LICENSE`（Apache-2.0 全文）与 `NOTICE`（版权与归属链）位于仓库根目录，改编文件与改编文档均已标注修改。
- [x] 发布前已扫描：包内不含 API key、账户信息、本机绝对路径或用户个人数据；`.gitignore` 排除缓存与打包产物。

## 四、商标与数据

「余额宝」「沪深 300」「中证」等名称仅为说明性指代，相关权利归各自权利人所有。本 Skill 不分发任何市场数据，不内置行情、费率、规模或财务数值；所有数字均须运行时取得或由用户提供并标注来源与时点。

## 五、引用事实的开源项目（未使用代码，v1.2.0 新增）

以下项目仅被引用**名称、许可证、公开接口与能力描述**，用于 `references/open-source-toolchain.md` 的选型表和 `scripts/quote_probe.py` 的端点字段核对。本 Skill **未复制其中任何实现代码**，也未分发其数据。许可证以 2026-11-11 的 GitHub API 声明**并回读仓库 LICENSE / README 原文**交叉核对为准；API 返回 `NOASSERTION` 或 `null`、或仓库发生迁移时，一律以 LICENSE 原文为准（OpenBB 即属此类，详见下文）。如未来引入代码，须先补齐许可证全文与版权行并在此登记。

| 项目 | 许可证 | 引用内容 | 未引用的部分 |
|---|---|---|---|
| `akfamily/akshare` | MIT | 能力范围、接口族名 | 全部实现代码与数据 |
| `akfamily/aktools` | MIT | HTTP / MCP 暴露方式 | 全部实现代码 |
| `rootSunc/CNEquity` | Apache-2.0 | 自托管数据湖能力、PIT/复权/MCP 特性 | 全部实现代码与数据 |
| `ranaroussi/yfinance` | Apache-2.0 | 港美股行情能力与限制 | 全部实现代码 |
| `dgunning/edgartools` | MIT | SEC 财报读取能力与 User-Agent 要求 | 全部实现代码 |
| `JerBouma/FinanceToolkit` | MIT | 财务比率能力描述 | 全部实现代码 |
| `ranaroussi/quantstats` | Apache-2.0 | 绩效指标能力描述 | 全部实现代码 |
| `dcajasn/Riskfolio-Lib` | BSD-3-Clause | 组合优化能力描述 | 全部实现代码 |
| `PyPortfolio/PyPortfolioOpt` | MIT | 有效前沿 / HRP / BL 能力描述 | 全部实现代码 |
| `OpenBB-finance/OpenBB` | Apache-2.0（main 分支 LICENSE + README 原文；API 为 NOASSERTION） | 仅记录其许可证与「不复制」边界 | 全部实现代码 |
| `mementum/backtrader` | GPL-3.0 | 仅记录其许可证与排除理由 | 全部实现代码 |
| `financial-datasets/mcp-server` | MIT | MCP server 能力与维护状态 | 全部实现代码 |

上述作者均未参与本 Skill 编写，也未为其结论背书。
