#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资金分层与分批建仓计算器（纯标准库，无市场数据）。

只依据用户提供的数值做确定性计算，不联网、不内置任何行情、费率或收益数据。
输出的档位比例、再平衡阈值与压测跌幅均为「可调整的规划假设」，不是市场事实或收益预测。

用法：
  python allocation_calc.py --total 120000 --monthly-expense 5000 \
      --emergency-months 6 --near-term 20000 --risk steady \
      --monthly-invest 2000 --build-months 12 --current-equity 0

  python allocation_calc.py --input params.json [--json]
  cat params.json | python allocation_calc.py --stdin [--json]

参数（JSON 文件用同样的键名，蛇形/连字符均可）：
  total               可投入金融资产总额（元，必填）
  monthly_expense     每月必要支出（元，默认 0）
  emergency_months    应急金目标月数（默认 6）
  near_term           1-3 年内确定要用的钱（元，默认 0）
  risk                conservative / steady / balanced / aggressive
  monthly_invest      每月可稳定投入金额（元，默认 0）
  build_months        计划分批建仓月数（默认 12）
  current_equity      当前已投权益金额（元，默认 0）
  rebalance_band      再平衡偏离阈值（百分点，默认 5）
  single_asset_cap    单只资产占权益仓位上限（%，默认 5）
  equity_ratio        显式覆盖风险档位对应的权益比例（0-1 之间，可选）
  stress_scenarios    权益下跌情景列表（%，默认 [20, 30]）
"""

import argparse
import json
import math
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RISK_EQUITY_RATIO = {
    "conservative": 0.20,
    "steady": 0.35,
    "balanced": 0.55,
    "aggressive": 0.75,
}
RISK_LABEL = {
    "conservative": "保守",
    "steady": "稳健",
    "balanced": "平衡",
    "aggressive": "积极",
}


def _num(value, default=0.0):
    if value is None or value == "":
        return float(default)
    return float(value)


def calculate(p):
    total = _num(p.get("total"))
    if total <= 0:
        raise ValueError("total（可投入金融资产总额）必须大于 0")

    monthly_expense = max(_num(p.get("monthly_expense")), 0.0)
    emergency_months = max(_num(p.get("emergency_months"), 6), 0.0)
    near_term = max(_num(p.get("near_term")), 0.0)
    monthly_invest = max(_num(p.get("monthly_invest")), 0.0)
    build_months = int(max(_num(p.get("build_months"), 12), 1))
    current_equity = max(_num(p.get("current_equity")), 0.0)
    rebalance_band = max(_num(p.get("rebalance_band"), 5), 0.0)
    single_asset_cap = max(_num(p.get("single_asset_cap"), 5), 0.0)

    scenarios_raw = p.get("stress_scenarios") or [20, 30]
    if isinstance(scenarios_raw, str):
        scenarios_raw = [float(x) for x in scenarios_raw.split(",") if x.strip()]
    stress_scenarios = [max(float(x), 0.0) for x in scenarios_raw]

    risk = str(p.get("risk") or "steady").lower()
    if risk not in RISK_EQUITY_RATIO:
        raise ValueError("risk 必须是 conservative / steady / balanced / aggressive 之一")

    equity_ratio = RISK_EQUITY_RATIO[risk]
    overridden = False
    if p.get("equity_ratio") not in (None, ""):
        equity_ratio = float(p["equity_ratio"])
        if not 0 <= equity_ratio <= 1:
            raise ValueError("equity_ratio 必须在 0 到 1 之间")
        overridden = True

    # 资金三层桶：第 0 层优先，第 1 层次之，剩余才是长期钱
    emergency_needed = monthly_expense * emergency_months
    layer0 = min(emergency_needed, total)
    layer1 = min(near_term, max(total - layer0, 0.0))
    layer2 = max(total - layer0 - layer1, 0.0)
    emergency_shortfall = max(emergency_needed - layer0, 0.0)
    ready = layer2 > 0 and emergency_shortfall == 0

    equity_target = layer2 * equity_ratio
    stabilizer_target = layer2 - equity_target
    equity_gap = max(equity_target - current_equity, 0.0)

    plan = {
        "status": "需先补齐应急金 / 长期资金不足" if not ready else "具备分批建仓条件",
        "required_per_period": 0.0,
        "actual_per_period": 0.0,
        "months_needed": 0,
        "note": "",
    }
    if ready and equity_gap > 0:
        required = equity_gap / build_months
        plan["required_per_period"] = round(required, 2)
        if monthly_invest <= 0:
            plan["actual_per_period"] = round(required, 2)
            plan["months_needed"] = build_months
            plan["note"] = "未提供每月可投金额，按计划月数均摊；请确认现金流能否支持"
        elif monthly_invest + 1e-9 >= required:
            plan["actual_per_period"] = round(required, 2)
            plan["months_needed"] = build_months
            plan["note"] = "月投额足以覆盖计划，多余结余留在现金层，不额外加码"
        else:
            plan["actual_per_period"] = round(monthly_invest, 2)
            plan["months_needed"] = math.ceil(equity_gap / monthly_invest)
            plan["note"] = "月投额不足以在计划月数内建仓，已按实际月投额延长周期；不可压缩应急金来凑"
    elif ready:
        plan["note"] = "当前权益金额已达或超过目标，无需新增建仓，进入再平衡检查"

    band_amount = layer2 * rebalance_band / 100
    single_asset_cap_amount = equity_target * single_asset_cap / 100

    stress = []
    if ready:
        for drop in stress_scenarios:
            loss = equity_target * drop / 100
            stress.append({
                "scenario": "权益部分下跌 {}%".format(drop),
                "equity_loss": round(loss, 2),
                "impact_on_layer2_pct": round(loss / layer2 * 100, 2) if layer2 else None,
                "impact_on_total_pct": round(loss / total * 100, 2),
            })

    warnings = []
    if emergency_shortfall > 0:
        warnings.append("应急金缺口 {:.2f} 元，先把每月结余补到第 0 层，暂不增加权益敞口".format(emergency_shortfall))
    if layer2 == 0:
        warnings.append("第 2 层长期资金为 0，当前不具备增加权益敞口的条件")
    if not ready:
        warnings.append("本次不输出目标配置比例与买入动作")
    if plan["months_needed"] > build_months:
        warnings.append("按当前月投额需 {} 个月，超过计划的 {} 个月；可延长周期或下调目标比例".format(plan["months_needed"], build_months))
    if current_equity > equity_target:
        warnings.append("当前权益金额高于目标比例，应评估再平衡而非继续加仓")

    if not ready:
        target_block = {
            "not_applicable": True,
            "reason": "应急金未备齐或第 2 层长期资金为 0，本次不输出目标配置比例、买入金额与压测结果",
        }
    else:
        target_block = {
            "risk_label": RISK_LABEL[risk],
            "equity_ratio": round(equity_ratio, 4),
            "equity_ratio_overridden": overridden,
            "equity_target": round(equity_target, 2),
            "stabilizer_target": round(stabilizer_target, 2),
            "equity_gap": round(equity_gap, 2),
            "single_asset_cap_pct": single_asset_cap,
            "single_asset_cap_amount": round(single_asset_cap_amount, 2),
            "rebalance_band_pct": rebalance_band,
            "rebalance_band_amount": round(band_amount, 2),
            "rebalance_trigger_range_pct": [
                round(max(equity_ratio * 100 - rebalance_band, 0), 2),
                round(min(equity_ratio * 100 + rebalance_band, 100), 2),
            ],
        }

    return {
        "inputs": {
            "total": total,
            "monthly_expense": monthly_expense,
            "emergency_months": emergency_months,
            "near_term": near_term,
            "risk": risk,
            "monthly_invest": monthly_invest,
            "build_months": build_months,
            "current_equity": current_equity,
        },
        "layers": {
            "layer0_emergency_needed": round(emergency_needed, 2),
            "layer0_emergency_actual": round(layer0, 2),
            "layer1_near_term": round(layer1, 2),
            "layer2_long_term": round(layer2, 2),
            "emergency_shortfall": round(emergency_shortfall, 2),
            "ready_for_equity": ready,
        },
        "targets": target_block,
        "build_plan": plan,
        "stress_scenarios": stress,
        "warnings": warnings,
        "assumptions": [
            "风险档位对应权益比例、再平衡阈值、单资产上限与压测跌幅均为可调整的规划假设，不是市场事实或收益预测",
            "分批建仓只降低一次性买入的路径依赖，不消除亏损风险",
            "单资产上限仅用于单只个股 / 主题类卫星仓；作为核心仓的宽基 ETF 应通过目标权重管理集中度",
            "未计入交易费用、税费与产品规则，实际执行前须向券商或基金管理人核实",
            "所有金额单位均为用户输入的同一币种单位（默认元）",
        ],
    }


def render(r):
    L, T, P = r["layers"], r["targets"], r["build_plan"]
    lines = []
    lines.append("=== 资金分层与分批建仓测算 ===")
    lines.append("结论：{}".format(P["status"]))
    lines.append("")
    lines.append("【资金三层桶】单位：与输入一致（默认元）")
    lines.append("  第 0 层 应急金   需 {:.2f} / 实留 {:.2f} / 缺口 {:.2f}".format(
        L["layer0_emergency_needed"], L["layer0_emergency_actual"], L["emergency_shortfall"]))
    lines.append("  第 1 层 短中期钱 {:.2f}".format(L["layer1_near_term"]))
    lines.append("  第 2 层 长期钱   {:.2f}   可承担权益波动：{}".format(
        L["layer2_long_term"], "是" if L["ready_for_equity"] else "否"))
    lines.append("")
    if L["ready_for_equity"]:
        lines.append("【目标配置】风险档位：{}，权益比例 {:.0f}%{}".format(
            T["risk_label"], T["equity_ratio"] * 100, "（用户覆盖）" if T["equity_ratio_overridden"] else ""))
        lines.append("  权益目标 {:.2f} / 稳健部分 {:.2f} / 待建仓缺口 {:.2f}".format(
            T["equity_target"], T["stabilizer_target"], T["equity_gap"]))
        lines.append("  单只个股/主题卫星仓参考上限 {:.0f}% = {:.2f}（宽基 ETF 核心仓不适用）；再平衡阈值 ±{:.0f} 个百分点（触发区间 {:.0f}%–{:.0f}%）".format(
            T["single_asset_cap_pct"], T["single_asset_cap_amount"],
            T["rebalance_band_pct"], T["rebalance_trigger_range_pct"][0], T["rebalance_trigger_range_pct"][1]))
        lines.append("")
        lines.append("【分批路径】计划 {} 个月；每期需 {:.2f}，实投 {:.2f}，实际需 {} 个月".format(
            r["inputs"]["build_months"], P["required_per_period"], P["actual_per_period"], P["months_needed"]))
        lines.append("  {}".format(P["note"]))
        lines.append("")
        lines.append("【下跌情景压测】仅为假设情景，不是预测")
        for s in r["stress_scenarios"]:
            lines.append("  {}：权益部分浮亏 {:.2f}，约占第 2 层 {:.2f}%、约占总额 {:.2f}%".format(
                s["scenario"], s["equity_loss"], s["impact_on_layer2_pct"], s["impact_on_total_pct"]))
    if r["warnings"]:
        lines.append("")
        lines.append("【提醒】")
        for w in r["warnings"]:
            lines.append("  - {}".format(w))
    lines.append("")
    lines.append("【假设声明】")
    for a in r["assumptions"]:
        lines.append("  - {}".format(a))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="资金分层与分批建仓计算器")
    ap.add_argument("--total", type=float)
    ap.add_argument("--monthly-expense", dest="monthly_expense", type=float)
    ap.add_argument("--emergency-months", dest="emergency_months", type=float, default=6)
    ap.add_argument("--near-term", dest="near_term", type=float, default=0)
    ap.add_argument("--risk", default="steady")
    ap.add_argument("--monthly-invest", dest="monthly_invest", type=float, default=0)
    ap.add_argument("--build-months", dest="build_months", type=float, default=12)
    ap.add_argument("--current-equity", dest="current_equity", type=float, default=0)
    ap.add_argument("--rebalance-band", dest="rebalance_band", type=float, default=5)
    ap.add_argument("--single-asset-cap", dest="single_asset_cap", type=float, default=5)
    ap.add_argument("--equity-ratio", dest="equity_ratio", type=float)
    ap.add_argument("--stress-scenarios", dest="stress_scenarios", default="20,30")
    ap.add_argument("--input", help="JSON 参数文件路径")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读 JSON")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    args = ap.parse_args()

    params = {}
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            params = json.load(f)
    elif args.stdin:
        params = json.load(sys.stdin)
    else:
        if args.total is None:
            ap.error("缺少 --total（或提供 --input / --stdin）")
        params = {
            "total": args.total,
            "monthly_expense": args.monthly_expense or 0,
            "emergency_months": args.emergency_months,
            "near_term": args.near_term,
            "risk": args.risk,
            "monthly_invest": args.monthly_invest,
            "build_months": args.build_months,
            "current_equity": args.current_equity,
            "rebalance_band": args.rebalance_band,
            "single_asset_cap": args.single_asset_cap,
            "equity_ratio": args.equity_ratio,
            "stress_scenarios": args.stress_scenarios,
        }

    try:
        result = calculate(params)
    except (ValueError, TypeError, KeyError) as e:
        print("输入错误：{}".format(e), file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(result))


if __name__ == "__main__":
    main()
