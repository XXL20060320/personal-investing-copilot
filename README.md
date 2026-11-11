# personal-investing-copilot

面向**个人投资者**的对话式理财与场内配置助手 Skill，主线是「现金理财（余额宝 / 货币基金）→ 场内 ETF 配置」的起步过渡，财报体检作为辅助能力。输出为结构化中文研报，不生成文件、不下单、不荐股。

- 版本：v1.2.2（交付级，含开源工具链选型）
- 许可证：**Apache-2.0**（`LICENSE`）；版权与第三方归属见 `NOTICE`
- 安装位置：`~/.workbuddy/skills/personal-investing-copilot/`（用户级，跨项目可用）
- 依赖：**无**。所有脚本仅用 Python 标准库，不内置任何市场数据，不要求 API key
- 语言：默认简体中文

## 它不是什么

- 不是量化交易系统，不接券商、不下单、不做技术分析择时。
- 不是机构级估值模型；不提供目标价、收益预测或「买入/卖出」指令。
- 不联网取数，除非你明确询问现价且环境允许（此时只调用公开只读行情端点）。
- 不替代持牌投资顾问；所有配置与动作建议都附固定免责声明。

## 快速开始

安装后新开会话（或刷新 Skill 列表）即可被自动识别。直接说：

```
我还在余额宝，场内该怎么配？
帮我对比 510300 和 159915 这两只 ETF
按我这份持仓做个体检（附 Excel/CSV）
帮我看下 XX 公司最新财报有没有雷
现在这个指数的估值算贵吗
最大回撤、HHI、跟踪误差是什么意思
```

也可以直接把财报 PDF、持仓 Excel / CSV 拖进对话。涉及买卖或配置比例时，它**会先问清资金期限、应急金、回撤承受与每月可投额**，前提不齐不给操作结论。

## 文件地图

```
SKILL.md                      触发条件、硬约束、决策树、脚本与资源索引（入口）
README.md                     本文件
CHANGELOG.md                  版本变更
LICENSE                       Apache-2.0 全文（本 Skill 自身许可）
NOTICE                        版权声明与第三方归属链
CONTRIBUTING.md               贡献指南、红线与提交前检查
THIRD_PARTY_NOTICES.md        第三方来源、许可证、引用范围与排除项
licenses/                     Apache-2.0 / MIT 许可证全文与上游 NOTICE
.gitignore                    排除缓存、打包产物与本地工具目录
references/
  onboarding-and-allocation.md    起步引导、资金三层桶、需运行时核实的规则、配置提醒
  etf-screening.md                ETF 身份核对、七维筛选、量化打分、跨境避坑
  financial-statement-review.md   三表联动、盈利与现金质量、异常信号
  valuation-and-entry.md          估值分位、条件化买卖与仓位框架
  portfolio-review.md             组合体检、集中度/相关性、再平衡与定投
  data-sources.md                 数据源注册表、字段契约、降级、运行日志、公开端点边界
  open-source-toolchain.md        开源取数/分析/组合工具的选型、许可证与接入边界
  data-and-compliance.md          检索路由、来源标注、五分法、固定免责模板
  beginner-explainer.md           六段式白话解释、术语表、适当性边界
  release-gates.md                红线、五类数据质检、PASS / NEED_REVIEW / BLOCK 门控
  output-templates.md             四类研报模板、输出契约、数据缺口声明
scripts/
  allocation_calc.py           资金分层、目标比例、分批/定投、再平衡阈值、下跌压测
  metrics_calc.py              财务比率、估值分位、HHI 集中度、相关性矩阵
  data_envelope.py             数据信封契约（来源/时点/口径/质量/哈希）
  quote_probe.py               可选公开行情快照探针（默认不联网）
  self_test.py                 离线交付自检门
examples/                     三个可照抄的示例对话
```

## 脚本用法

```bash
cd ~/.workbuddy/skills/personal-investing-copilot

# 起步配置：正常场景（单位为同一币种，默认元）
python scripts/allocation_calc.py --total 120000 --monthly-expense 5000 \
  --emergency-months 6 --near-term 20000 --risk steady \
  --monthly-invest 2000 --build-months 12

# 输出 JSON 供研报引用
python scripts/allocation_calc.py --total 120000 --monthly-expense 5000 --risk balanced --json

# 指标计算：从标准输入读 JSON（财务 / 估值 / 组合 / 收益序列按需提供）
python scripts/metrics_calc.py --stdin --json < payload.json

# 数据信封示例与自检
python scripts/data_envelope.py --demo
python scripts/data_envelope.py --self-test

# 可选：仅当用户明确问现价时（只发送标的代码）
python scripts/quote_probe.py --codes 510300 159915

# 交付自检（不联网、不改文件）
python scripts/self_test.py
```

`allocation_calc.py` 在应急金不足时会返回 `targets.not_applicable = true` 且不输出压测金额，含义是「当前不具备增加权益敞口的条件」，不是「建议 0% 权益」。

所有默认参数（风险档位比例、再平衡阈值、单资产上限、压测跌幅）都是**可调整的规划假设**，不是市场事实，也不是收益预测。脚本不内置行情、费率、规模或财务数值。

## 数据与隐私

- 数据来源按「金融 MCP → `domain_search` → `WebSearch`」逐级降级；一手披露优先于聚合器。
- 每个关键数字带来源 + 时点 + 口径；失败与降级必须留痕，质量标记非 `ok` 时显式说明。
- `quote_probe.py` 是**唯一**联网脚本，仅在用户明确问现价时调用，支持 A 股 / 港股 / 美股，只向公开只读端点发送标的代码，**不发送持仓、金额、账户或其他个人信息**，不写本地文件。
- 用户上传的 PDF / Excel / CSV 只用于当次分析，标注「用户提供，需核实」。

## 合规与第三方引用

本 Skill 合规吸收了开源项目的方法论与少量数据结构，完整署名、许可证全文与修改说明见 `THIRD_PARTY_NOTICES.md`：

- Apache-2.0：`china-stock-fund-analysis`（数据契约、数据源注册表、小白解释层、输出契约）
- MIT：`anchor-and-tilt`、`himself65/finance-skills`、`tradermonty/claude-trading-skills`（确定性规则、量化打分、数据质检、门控分级）
- 许可证声明不完整的 `asfamilybank/stock-query`：**仅采用公开端点与代码位数等事实信息，未使用任何实现代码**
- 无许可证的仓库：一律排除

上游作者未参与本 Skill 编写，也未为其结论背书。

## 开源许可与发布到 GitHub

- 本项目自建部分采用 **Apache License 2.0**（根目录 `LICENSE`）；版权声明与第三方归属见 `NOTICE`。`licenses/` 里的是各上游自己的许可证全文，不代表本项目整体授权。
- 为什么是 Apache-2.0：`scripts/data_envelope.py` 改编自 Apache-2.0 项目，同许可证可避免混合授权；专利授权明确；第 4 条要求的保留 NOTICE、标注修改、不暗示背书，本项目已逐文件履行（见各 references 文首与 `data_envelope.py` 头部）。
- 贡献与二次分发规则见 `CONTRIBUTING.md`：可商用、可修改、可再分发，但须保留 `LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md` 与 `licenses/` 全部文件并标注修改。

发布步骤：

1. 确认版权行。`NOTICE` 首部为 `Copyright 2026 personal-investing-copilot contributors`；要改成你的姓名或 GitHub ID，改这一行即可，其余文件不依赖它。
2. 把整个目录推到新仓库（`LICENSE`、`NOTICE` 必须入库；`.gitignore` 已排除 `__pycache__/`、`*.zip` 与本地工具目录）：

   ```bash
   cd personal-investing-copilot
   python scripts/self_test.py            # 发布前自检
   git init
   git add .
   git commit -m "Initial release: personal-investing-copilot v1.2.2"
   git remote add origin https://github.com/<your-id>/personal-investing-copilot.git
   git branch -M main
   git push -u origin main
   ```

   GitHub 会自动把根目录 `LICENSE` 识别为 Apache-2.0；若未显示，检查文件名必须是无扩展名的 `LICENSE` 且全文未被截断。

3. 推送前再跑一次 `python scripts/self_test.py`，确认含「开源发布」在内全部检查通过。
4. 可选：仓库描述「面向个人投资者的场内 ETF 配置起步助手 Skill」；topics `agent-skills` / `claude-skills` / `workbuddy` / `etf` / `portfolio` / `personal-finance` / `a-shares`。

仓库内不含 API key、账户信息、本机绝对路径或任何用户个人数据；示例对话中的金额均为虚构演示值。

## 维护

修改任何文件后运行 `python scripts/self_test.py`，它会检查脚本语法、正常与边界场景、数据契约、文档/许可证完整性、SKILL.md 的资源引用，以及对外发布所需的 LICENSE / NOTICE / 敏感信息扫描。分发时用 skill-creator 的 `package_skill.py` 重新打包；压缩包应包含 `LICENSE`、`NOTICE` 与 `licenses/` 全部文件。

## 免责声明

本 Skill 输出基于公开数据、用户提供的数值与确定性计算，仅供参考，不构成投资建议。市场有风险，投资需谨慎；过往表现不预示未来收益。交易规则、费用与产品条款请以券商、交易所和基金管理人最新公示为准。
