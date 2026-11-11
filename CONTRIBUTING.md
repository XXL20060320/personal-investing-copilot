# 贡献指南

欢迎提交 Issue 与 Pull Request。这个 Skill 的定位是「给个人投资者的配置纪律助手」，不是荐股工具或量化策略库，贡献请守住下面的红线。

## 许可证与贡献授权

本项目采用 **Apache License 2.0**（见 `LICENSE`），版权与第三方归属见 `NOTICE`。提交贡献即表示你同意你的贡献按 Apache-2.0 授权，并确认你有权提交该内容；本项目不要求签署 CLA。

下游可以商用、修改、再分发，但必须保留 `LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md` 与 `licenses/` 全部文件，标注被修改的文件，且不得暗示上游作者或本项目为你背书。

## 不可逾越的红线

1. **不引入许可证不完整的第三方代码**。引入前先在 GitHub API 与仓库 LICENSE / README 原文交叉核对；`NOASSERTION`、`null`、只有 README 声明或仓库已迁移而无法确认的，最多只取事实性信息（端点域名、代码位数等），不得复制实现代码。新增引用必须登记到 `THIRD_PARTY_NOTICES.md`、`NOTICE` 与 `licenses/`。
2. **不内置市场数据、API key、账户信息或任何用户个人数据**。脚本保持纯 Python 标准库，不新增第三方依赖，不写本地文件。
3. **不编造数字**。行情、费率、规模、财务数值一律运行时取得或由用户提供，每个关键数字带「来源 + 时点 + 口径」。
4. **场内规则运行时核实**。交易时间、费用、申赎、涨跌幅、跨境额度等不得凭记忆写死，写进文档的规则必须附带「以券商 / 交易所 / 基金管理人最新公示为准」。
5. **不输出交易指令**。不荐股、不给目标价与收益预测；涉及买卖或配置比例时先问清资金期限、应急金、回撤承受与每月可投额，前提缺失不给操作结论，末尾附固定免责声明。
6. **颜色约定**：A 股涨红跌绿，境外市场不套用该约定。

## 提交前检查

```bash
cd personal-investing-copilot
python scripts/self_test.py            # 离线自检：脚本、契约、文档、许可证链、发布检查
python scripts/quote_probe.py --self-test   # 行情探针离线自检
```

改动文档后同时更新 `CHANGELOG.md`、`README.md` 的文件地图与 `SKILL.md` 的资源索引；改动版本时同步三处版本号。分发前用 skill-creator 的 `package_skill.py` 重新打包，确认压缩包内含 `LICENSE`、`NOTICE` 与 `licenses/` 全部文件。

## 新增第三方内容的操作清单

- [ ] 确认许可证（API + LICENSE 原文；`NOASSERTION` 必须回读原文）
- [ ] 把许可证全文（含版权行）放入 `licenses/`
- [ ] 在被改编的文件头部或文首写明出处、许可证与修改清单
- [ ] 更新 `THIRD_PARTY_NOTICES.md`（引用范围 + 修改说明 + 排除项）与 `NOTICE`
- [ ] 在 `self_test.py` 的 `REQUIRED_FILES` 中登记新文件
- [ ] 运行全量自检

## 行为约定

就事论事，讨论方法与证据，不评价用户的资金决策，不在 Issue 里索要或公开他人的持仓、账户与财务明细。
