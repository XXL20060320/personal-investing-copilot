#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线交付自检门：脚本、契约、文档、许可证与引用完整性。

结构性借鉴 Apache-2.0 项目 ``china-stock-fund-analysis`` 的
``scripts/validate_skill.py``（依赖无关冒烟检查 / 临时 fixture / JSON 结果 /
快速失败），实现针对本 Skill 独立重写，未复制其业务校验代码。
署名与许可证见 ``THIRD_PARTY_NOTICES.md``。

用法::

    python scripts/self_test.py            # 全部检查，输出 JSON
    python scripts/self_test.py --quiet    # 只输出结论行

不联网、不读用户数据、不修改 Skill 包内任何文件。失败时退出码为 1。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REFS = ROOT / "references"

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "THIRD_PARTY_NOTICES.md",
    "LICENSE",
    "NOTICE",
    "CONTRIBUTING.md",
    ".gitignore",
    "licenses/Apache-2.0.txt",
    "licenses/NOTICE-upstream.txt",
    "licenses/MIT-anchor-and-tilt.txt",
    "licenses/MIT-finance-skills.txt",
    "licenses/MIT-claude-trading-skills.txt",
    "references/data-and-compliance.md",
    "references/data-sources.md",
    "references/beginner-explainer.md",
    "references/release-gates.md",
    "references/onboarding-and-allocation.md",
    "references/etf-screening.md",
    "references/financial-statement-review.md",
    "references/valuation-and-entry.md",
    "references/portfolio-review.md",
    "references/output-templates.md",
    "references/open-source-toolchain.md",
    "scripts/allocation_calc.py",
    "scripts/metrics_calc.py",
    "scripts/data_envelope.py",
    "scripts/quote_probe.py",
    "scripts/self_test.py",
    "examples/onboarding.md",
    "examples/etf-compare.md",
    "examples/portfolio-checkup.md",
]

PY_SCRIPTS = [
    "allocation_calc.py",
    "metrics_calc.py",
    "data_envelope.py",
    "quote_probe.py",
    "self_test.py",
]


class CheckFailure(RuntimeError):
    pass


def run_py(args: list[str], stdin_text: str | None = None) -> str:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PYTHONUTF8", "1")
    proc = subprocess.run(
        [sys.executable, *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(SCRIPTS),
        timeout=30,
    )
    if proc.returncode != 0:
        raise CheckFailure(
            "命令失败：{}\nstdout: {}\nstderr: {}".format(" ".join(args), proc.stdout, proc.stderr)
        )
    return proc.stdout


def check_syntax() -> str:
    for name in PY_SCRIPTS:
        path = SCRIPTS / name
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    return "syntax: {} 个脚本编译通过".format(len(PY_SCRIPTS))


def check_allocation() -> str:
    out = run_py(
        [
            "allocation_calc.py",
            "--total", "120000",
            "--monthly-expense", "5000",
            "--emergency-months", "6",
            "--near-term", "20000",
            "--risk", "steady",
            "--monthly-invest", "2000",
            "--build-months", "12",
            "--json",
        ]
    )
    data = json.loads(out)
    if not data["layers"]["ready_for_equity"]:
        raise CheckFailure("正常场景应判定具备分批建仓条件")
    if not (0 < data["targets"]["equity_ratio"] < 1):
        raise CheckFailure("正常场景目标权益比例异常")
    if not data["stress_scenarios"] or "assumptions" not in data:
        raise CheckFailure("正常场景缺少压测或规划假设标注")
    return "allocation_calc: 正常场景 + 假设标注"


def check_allocation_boundary() -> str:
    out = run_py(
        [
            "allocation_calc.py",
            "--total", "20000",
            "--monthly-expense", "5000",
            "--emergency-months", "6",
            "--risk", "aggressive",
            "--monthly-invest", "3000",
            "--json",
        ]
    )
    data = json.loads(out)
    if data["targets"].get("not_applicable") is not True:
        raise CheckFailure("应急金不足时应返回 not_applicable，而不是 0% 目标比例")
    if data["stress_scenarios"]:
        raise CheckFailure("不具备入场条件时不应输出下跌压测金额")
    if not any("不输出目标配置比例" in w for w in data["warnings"]):
        raise CheckFailure("边界场景缺少明确警示")
    return "allocation_calc: 应急金不足边界（not_applicable）"


def check_metrics() -> str:
    payload = {
        "financial": {
            "revenue": 1000, "revenue_prev_year": 800, "net_profit": 120,
            "gross_profit": 350, "operating_cash_flow": 90,
            "accounts_receivable": 200, "total_assets": 2000,
            "total_liabilities": 900, "equity": 1100,
        },
        "valuation": {"label": "示例指数 PE", "pe_series": [12, 15, 18, 22, 16], "current_pe": 18},
        "portfolio": {
            "as_of": "2026-11-10",
            "holdings": [
                {"name": "示例A", "code": "510300", "value": 30000},
                {"name": "示例B", "code": "511260", "value": 20000},
            ],
            "target_weights": {"510300": 0.6, "511260": 0.4},
        },
        "returns": {"510300": [0.01, -0.02, 0.015, 0.008], "511260": [0.002, 0.001, -0.001, 0.0]},
    }
    out = run_py(["metrics_calc.py", "--stdin", "--json"], json.dumps(payload, ensure_ascii=False))
    data = json.loads(out)
    for key in ("financial", "valuation", "portfolio", "correlations"):
        if key not in data:
            raise CheckFailure("metrics_calc 缺少模块输出：{}".format(key))
    if "hhi" not in json.dumps(data["portfolio"], ensure_ascii=False).lower():
        raise CheckFailure("组合模块缺少集中度指标")
    return "metrics_calc: 财务 / 估值 / 组合 / 相关性四模块"


def check_envelope_and_probe() -> str:
    env_out = json.loads(run_py(["data_envelope.py", "--self-test"]))
    probe_out = json.loads(run_py(["quote_probe.py", "--self-test"]))
    if env_out["status"] != "ok" or probe_out["status"] != "ok":
        raise CheckFailure("数据信封或行情探针离线自检失败")
    return "data_envelope + quote_probe: 离线契约自检（未联网）"


def check_documents() -> str:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        raise CheckFailure("缺少交付文件：{}".format(", ".join(missing)))

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---") or "name: personal-investing-copilot" not in skill[:600]:
        raise CheckFailure("SKILL.md frontmatter 的 name 缺失或格式异常")
    if "description:" not in skill[:1200]:
        raise CheckFailure("SKILL.md frontmatter 缺少 description")

    # SKILL.md 里出现的资源引用必须真实存在
    referenced = set(re.findall(r"(?:references|scripts|examples|licenses)/[A-Za-z0-9_.-]+\.(?:md|py|txt)", skill))
    broken = sorted(name for name in referenced if not (ROOT / name).is_file())
    if broken:
        raise CheckFailure("SKILL.md 引用了不存在的文件：{}".format(", ".join(broken)))

    compliance = (ROOT / "references/data-and-compliance.md").read_text(encoding="utf-8")
    for token in ("模板 A", "模板 B", "免责声明", "风险提示与免责声明"):
        if token not in compliance:
            raise CheckFailure("免责声明固定模板不完整，缺少：{}".format(token))

    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    if "Apache-2.0" not in notices or "未复制" not in notices:
        raise CheckFailure("第三方署名文件缺少许可证或排除说明")

    apache = (ROOT / "licenses/Apache-2.0.txt").read_text(encoding="utf-8")
    if "Apache License" not in apache or "Version 2.0" not in apache:
        raise CheckFailure("Apache-2.0 许可证全文不完整")
    for name in ("MIT-anchor-and-tilt.txt", "MIT-finance-skills.txt", "MIT-claude-trading-skills.txt"):
        text = (ROOT / "licenses" / name).read_text(encoding="utf-8")
        if "MIT License" not in text or "Copyright" not in text:
            raise CheckFailure("MIT 许可证全文或版权行缺失：{}".format(name))
    upstream = (ROOT / "licenses/NOTICE-upstream.txt").read_text(encoding="utf-8")
    if "anthropics/financial-services" not in upstream:
        raise CheckFailure("上游 NOTICE 声明链缺失")

    return "文档: {} 个必需文件 / {} 条资源引用 / 免责模板 / 许可证链".format(
        len(REQUIRED_FILES), len(referenced)
    )


def check_toolchain_doc() -> str:
    doc = (REFS / "open-source-toolchain.md").read_text(encoding="utf-8")
    # 注意：'GPL-3.0' 是 'AGPL-3.0' 的子串，只做 token 存在性检查无法发现许可证写错，
    # 且会把错误声明固化成「自检必需」。因此必须显式拦截已核实的过期表述。
    for token in ("MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0", "未复制任何实现代码"):
        if token not in doc:
            raise CheckFailure("开源工具链文档缺少关键信息：{}".format(token))
    for stale in ("AGPL-3.0（官方公告）", "避免 AGPL 传染", "重点：OpenBB 的 AGPL", "OpenBB MCP | AGPL-3.0"):
        if stale in doc:
            raise CheckFailure("开源工具链文档含已核实的过期许可证声明：{}".format(stale))
    return "开源工具链: 许可证分层、排除项、署名边界与过期声明拦截齐全"


def check_compliance_markers() -> str:
    envelope = (SCRIPTS / "data_envelope.py").read_text(encoding="utf-8")
    probe = (SCRIPTS / "quote_probe.py").read_text(encoding="utf-8")
    if "Apache-2.0" not in envelope or "改编自" not in envelope:
        raise CheckFailure("data_envelope.py 缺少上游署名与许可证标注")
    if "未使用其任何代码" not in probe:
        raise CheckFailure("quote_probe.py 缺少未复制代码的合规说明")
    return "代码署名: 改编声明与未复制声明均存在"


def check_public_release() -> str:
    """发布前检查：项目自身许可证、第三方归属链与敏感信息，不联网。"""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    for token in ("Apache License", "Version 2.0, January 2004", "END OF TERMS AND CONDITIONS", "APPENDIX"):
        if token not in license_text:
            raise CheckFailure("根 LICENSE 不是完整的 Apache-2.0 全文：缺少 {}".format(token))

    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    for token in ("Copyright", "Apache License", "china-stock-fund-analysis", "NOTICE-upstream.txt", "未参与"):
        if token not in notice:
            raise CheckFailure("NOTICE 缺少必要归属信息：{}".format(token))

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "Apache-2.0" not in readme or "## 开源许可与发布到 GitHub" not in readme:
        raise CheckFailure("README 缺少许可证或 GitHub 发布说明")

    third = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    if "未指定对外开源许可证" in third:
        raise CheckFailure("THIRD_PARTY_NOTICES 仍声明本 Skill 未指定许可证")

    # 对外发布不得夹带本机绝对路径或硬编码凭证。
    candidates = list(ROOT.rglob("*.md")) + list((ROOT / "scripts").glob("*.py"))
    candidates += [ROOT / name for name in ("LICENSE", "NOTICE", ".gitignore") if (ROOT / name).is_file()]
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"[A-Za-z]:[\\/]Users[\\/]", text):
            raise CheckFailure("交付包含本机绝对路径：{}".format(path.relative_to(ROOT)))
        if re.search(r"(?i)\b(api[_-]?key|token|password)\s*=\s*['\"][A-Za-z0-9_-]{12,}", text):
            raise CheckFailure("交付疑似包含硬编码凭证：{}".format(path.relative_to(ROOT)))

    return "开源发布: LICENSE 全文 / NOTICE 归属 / README 声明 / 署名一致 / 敏感信息扫描通过"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true", help="只打印一行结论")
    args = parser.parse_args()

    checks: list[str] = []
    try:
        for func in (
            check_syntax,
            check_allocation,
            check_allocation_boundary,
            check_metrics,
            check_envelope_and_probe,
            check_documents,
            check_toolchain_doc,
            check_compliance_markers,
            check_public_release,
        ):
            checks.append(func())
    except (CheckFailure, subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        payload = {"status": "failed", "passed": checks, "error": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    payload: dict[str, Any] = {
        "status": "ok",
        "skill": "personal-investing-copilot",
        "checks": checks,
        "note": "离线自检通过仅代表工程完整，语义质检仍需按 references/release-gates.md 执行",
    }
    if args.quiet:
        print("SELF_TEST OK ({} checks)".format(len(checks)))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
