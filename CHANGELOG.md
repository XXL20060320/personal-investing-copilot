# 变更记录

## v1.2.2 — 2026-11-11（对外开源许可与发布准备）

### 新增

- `LICENSE`：项目整体采用 **Apache License 2.0** 全文。选择理由：核心数据契约改编自 Apache-2.0 项目，同许可证避免混合授权；自带专利授权；其第 4 条要求的 NOTICE 与修改标注本项目已逐文件履行。
- `NOTICE`：版权行 + 完整第三方归属链（含上游 NOTICE 原文引用、MIT 版权行、事实性引用边界、商标与不背书声明），满足 Apache-2.0 §4(d)。
- `CONTRIBUTING.md`：贡献授权、六条红线、提交前检查与「新增第三方内容」清单；`.gitignore`：排除缓存、打包产物与本地工具目录。
- `self_test.py` 新增 `check_public_release()`：校验 LICENSE 全文、NOTICE 归属、README 发布说明、署名一致性，并扫描包内本机绝对路径。

### 变更

- `THIRD_PARTY_NOTICES.md`：删除「未指定对外开源许可证」，改为 Apache-2.0 声明与下游保留义务；合规清单补两项。
- `README.md`：新增「开源许可与发布到 GitHub」章节、许可证元信息与文件地图；`SKILL.md`：版本升至 v1.2.2，资源索引补许可证文件。

## v1.2.1 — 2026-11-11（复核修正）

### 修复

- **许可证事实错误**：`OpenBB-finance/OpenBB` 由误记的 AGPL-3.0 更正为 **Apache-2.0**（依据 main 分支 LICENSE 首句与 README「3. License」）；排除理由改为「重量级数据平台、本 Skill 不接入」，不再援引 AGPL 传染。同步修正 `THIRD_PARTY_NOTICES.md`、`SKILL.md`、`README.md`，并在 `self_test.py` 加入过期声明拦截。
- **行情探针**：支持 5 位裸港股代码；修复混合市场时 `request.markets` 被降级循环裁剪导致只显示剩余市场；`expected` 改按唯一规范化代码计数（重复输入不误报），同时对被拒绝的入参强制降级为 PARTIAL 并列出原因，避免静默跳过；跨市场请求增加时区口径提示。质量标记分支已纳入离线自检。
- 补充 `data-sources.md` 时区与字段说明、`output-templates.md` 跨境快照输出契约，以及 aktools 在 WorkBuddy 中的准确 MCP 接入方式。

## v1.2.0 — 2026-11-11（开源工具链与港美快照）

### 新增

- `references/open-source-toolchain.md`：按任务列出 AKShare、aktools、CNEquity、yfinance、edgartools、FinanceToolkit、quantstats、Riskfolio-Lib、PyPortfolioOpt 的许可证、能力、入口与风险；列明 OpenBB（Apache-2.0，重量级平台）与 backtrader（GPL-3.0）的排除理由；给出 MCP server 清单、接入判断顺序与季度复核清单。
- `scripts/self_test.py` 新增 `check_toolchain_doc`，校验新文档的许可证分层与「未复制代码」声明。

### 变更

- `scripts/quote_probe.py`：`--codes` 支持港股（`hk00700` / `00700.HK`）与美股（`usAAPL` / `AAPL.US` / 裸 ticker）；返回 `currency`；时间戳解析按 A 股 / 港股 / 美股分支；自检覆盖三市场映射。
- `references/data-sources.md`：L4 层补开源封装清单与许可证；第 7 节扩展为三市场端点与字段位置对照表。
- `references/data-and-compliance.md`：路由第 1 层明确包含用户自建 MCP（aktools / CNEquity）；行情探针注明支持三市场。
- `SKILL.md`：版本升至 v1.2.0；决策树新增「开源工具选型」；脚本清单与资源索引同步；硬约束 3 补「不得假设用户已装开源库」。

## v1.1.0 — 2026-11-10（交付级打磨）

以自建的「现金理财 → 场内 ETF 配置」起步路径为主体，合规吸收已核实的开源实现，补齐交付所需的工程与合规层。**未整包安装任何第三方 Skill，未引入任何市场数据或 API key。**

### 新增：合规与署名

- `THIRD_PARTY_NOTICES.md`：逐仓库列明许可证、引用类型、对应文件、修改说明与明确排除项。
- `licenses/`：Apache-2.0 全文、上游 NOTICE 原文（保留对 `anthropics/financial-services` 的声明链）、三份 MIT 全文（含版权行）。
- 明确边界：`asfamilybank/stock-query` 声明 MIT 但 GitHub API `license=null` 且无 LICENSE 文件，故**只采用事实性信息、未复制代码**；无许可证仓库一律排除。

### 新增：方法论文档

- `references/data-sources.md`：数据源分层注册表、标准化字段契约、降级顺序、运行日志、公开端点边界、数据质量门槛。
- `references/beginner-explainer.md`：六段式白话解释、起步阶段专属翻译、术语表、脚本结果翻译、适当性边界。
- `references/release-gates.md`：PASS / NEED_REVIEW / BLOCK 三态门控、10 条红线、软性问题、五类数据质检、确定性与假设显式化、交付自检。

### 新增：脚本

- `scripts/data_envelope.py`：改编自 Apache-2.0 上游 `contracts.py`，文件头保留出处/许可证/修改说明；新增交易状态与备注字段、`--demo` / `--self-test`。
- `scripts/quote_probe.py`：独立实现的可选公开行情快照探针，输出带来源链与质量标记的数据信封；失败返回 `unverifiable` 并降级，不凭记忆补价。
- `scripts/self_test.py`：离线交付自检门，覆盖脚本语法、正常/边界场景、数据契约、文档与许可证完整性、SKILL.md 资源引用。

### 改写：既有文档

- `SKILL.md`：新增版本信息、硬约束第 10/11 条（五分法与假设显式化、门控与合规引用），决策树增加「小白解释 / 取数与来源争议 / 现价 / 定稿门控」路径，脚本清单从 2 个扩到 5 个，资源索引补齐。
- `data-and-compliance.md`：新增五类表述分开、数据信封与运行日志、行情探针边界、第三方代码许可证边界；自检清单补 4 项并联动门控文档。
- `etf-screening.md`：新增逐项打分（League Table 思路）与 6 条红旗；补折溢价口径出处。
- `portfolio-review.md`：新增分析前数据质检与穿透检查、指标白话翻译要求。
- `output-templates.md`：新增七项输出契约、输出前门控与解释层触发规则，明确运行记录必须放在免责声明之前。

### 新增：交付物

- `README.md`（安装、文件地图、脚本命令、隐私与合规、维护）、`CHANGELOG.md`、`examples/` 三个示例对话。

## v1.0.0 — 2026-11-10（初版）

- 建立 Skill 骨架与 `SKILL.md`（9 条硬约束、决策树、Step 0 前提确认、输出规范）。
- 7 份 references：起步配置、ETF 七维筛选、财报体检、估值与条件化买卖、持仓体检、数据合规与免责模板、四类研报模板。
- 2 个纯标准库脚本：`allocation_calc.py`、`metrics_calc.py`；修复「应急金不足时 JSON 仍输出 0% 目标比例」的边界问题，改为 `not_applicable`。
- 通过结构校验与打包，交付 `personal-investing-copilot.zip`。
