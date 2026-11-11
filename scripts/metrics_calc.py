#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""财务比率 / 估值分位 / 组合集中度计算（纯标准库，无市场数据）。

只依据用户提供的数值做确定性计算，不联网、不内置任何公司或行情数据。
输入 JSON 中可包含任意组合的 section：financial / valuation / portfolio / returns。
输出须在研报中标注「依据用户提供的数值计算」与数据报告期 / 导出日期。

用法：
  python metrics_calc.py --input data.json [--json]
  cat data.json | python metrics_calc.py --stdin [--json]

输入示例：
{
  "period": "2025Q3",
  "unit": "万元",
  "financial": {
    "revenue": 1000, "revenue_prev_year": 800, "revenue_prev_quarter": 950,
    "net_profit": 120, "net_profit_prev_year": 100, "gross_profit": 350,
    "operating_cash_flow": 90, "accounts_receivable": 200,
    "total_assets": 2000, "total_liabilities": 900, "equity": 1100
  },
  "valuation": {"label": "某指数 PE", "pe_series": [12, 15, 18, 22, 16], "current_pe": 18},
  "portfolio": {
    "as_of": "2026-11-10",
    "holdings": [{"name": "A", "code": "510300", "value": 30000},
                 {"name": "B", "code": "511260", "value": 20000}],
    "target_weights": {"510300": 0.6, "511260": 0.4},
    "single_asset_cap_pct": 5, "rebalance_band_pct": 5
  },
  "returns": {"510300": [0.01, -0.02, 0.015], "511260": [0.002, 0.001, -0.001]}
}
"""

import argparse
import json
import math
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _f(v):
    if v is None or v == "":
        return None
    return float(v)


def _r(v, n=4):
    return None if v is None else round(v, n)


def change(cur, base):
    """同比 / 环比变动百分比；基期为零或缺失时返回 None，绝不臆造。"""
    cur, base = _f(cur), _f(base)
    if cur is None or base is None or base == 0:
        return None
    return (cur - base) / abs(base) * 100


def ratio(num, den):
    num, den = _f(num), _f(den)
    if num is None or den is None or den == 0:
        return None
    return num / den * 100


def financial(f):
    out = {
        "period": f.get("period", "未提供"),
        "unit": f.get("unit", "未提供"),
        "currency": f.get("currency", "未提供"),
        "yoy_revenue_pct": _r(change(f.get("revenue"), f.get("revenue_prev_year")), 2),
        "qoq_revenue_pct": _r(change(f.get("revenue"), f.get("revenue_prev_quarter")), 2),
        "yoy_net_profit_pct": _r(change(f.get("net_profit"), f.get("net_profit_prev_year")), 2),
        "gross_margin_pct": _r(ratio(f.get("gross_profit"), f.get("revenue")), 2),
        "net_margin_pct": _r(ratio(f.get("net_profit"), f.get("revenue")), 2),
        "cash_content_pct": _r(ratio(f.get("operating_cash_flow"), f.get("net_profit")), 2),
        "receivable_to_revenue_pct": _r(ratio(f.get("accounts_receivable"), f.get("revenue")), 2),
        "debt_ratio_pct": _r(ratio(f.get("total_liabilities"), f.get("total_assets")), 2),
        "roe_pct": _r(ratio(f.get("net_profit"), f.get("equity")), 2),
    }
    flags = []
    if out["cash_content_pct"] is not None and out["cash_content_pct"] < 80:
        flags.append("经营现金流 / 净利润低于 80%：需核实回款、应收与利润质量")
    if out["yoy_revenue_pct"] is not None and out["yoy_net_profit_pct"] is not None:
        if out["yoy_net_profit_pct"] - out["yoy_revenue_pct"] > 20:
            flags.append("利润增速显著快于收入增速：核实是否来自一次性损益或费用收缩")
    if out["receivable_to_revenue_pct"] is not None and out["receivable_to_revenue_pct"] > 50:
        flags.append("应收占收入比重偏高：核对应收周转与账龄")
    if out["debt_ratio_pct"] is not None and out["debt_ratio_pct"] > 70:
        flags.append("资产负债率偏高：核对有息负债结构与行业特性")
    out["flags"] = flags
    out["note"] = "阈值仅为提示用的经验刻度，需结合行业与口径判断，不构成结论；ROE 按当期净利润 / 期末净资产简化计算，非加权平均净资产口径"
    return out


def valuation(v):
    series = [_f(x) for x in (v.get("pe_series") or []) if _f(x) is not None]
    current = _f(v.get("current_pe"))
    out = {
        "label": v.get("label", "未提供"),
        "sample_size": len(series),
        "sample_range": v.get("sample_range", "未提供"),
        "current_pe": current,
        "min": _r(min(series), 2) if series else None,
        "median": _r(statistics.median(series), 2) if series else None,
        "max": _r(max(series), 2) if series else None,
    }
    if series and current is not None:
        below = sum(1 for x in series if x <= current)
        out["percentile_pct"] = _r(below / len(series) * 100, 2)
    else:
        out["percentile_pct"] = None
    out["flags"] = []
    if len(series) < 20:
        out["flags"].append("样本量偏少（{} 个观测），分位结论稳定性有限；判断历史分位需长周期且覆盖完整周期".format(len(series)))
    if out["sample_range"] == "未提供":
        out["flags"].append("缺少样本区间标注，须补充数据来源与统计周期后才能写入研报")
    out["note"] = "分位是读数不是买卖信号；30% 以下偏低 / 30%-70% 中性 / 70% 以上偏高为经验刻度"
    return out


def pearson(a, b):
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[:n], b[:n]
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da == 0 or db == 0:
        return None
    return num / (da * db)


def portfolio(p):
    holdings = p.get("holdings") or []
    total = sum(_f(h.get("value")) or 0 for h in holdings)
    out = {"as_of": p.get("as_of", "未提供"), "total_value": _r(total, 2), "holdings": []}
    if total <= 0:
        out["error"] = "持仓金额合计必须大于 0"
        return out

    cap = _f(p.get("single_asset_cap_pct"))  # 未提供则不擅自替用户设定集中度纪律
    band = _f(p.get("rebalance_band_pct"))
    if band is None:
        band = 5.0
    targets = p.get("target_weights") or {}
    hhi = 0.0
    breaches, deviations = [], []

    for h in holdings:
        value = _f(h.get("value")) or 0.0
        w = value / total
        hhi += w ** 2
        code = str(h.get("code", ""))
        item = {
            "name": h.get("name", "未提供"),
            "code": code,
            "value": _r(value, 2),
            "weight_pct": _r(w * 100, 2),
        }
        if code in targets:
            tw = _f(targets[code])
            if tw is not None:
                tw = tw * 100 if tw <= 1 else tw
                dev = w * 100 - tw
                item["target_weight_pct"] = _r(tw, 2)
                item["deviation_pp"] = _r(dev, 2)
                item["rebalance_triggered"] = abs(dev) > band
                if abs(dev) > band:
                    deviations.append("{}（{}）偏离目标 {:+.2f} 个百分点".format(item["name"], code, dev))
        if cap is not None and w * 100 > cap:
            breaches.append("{}（{}）占比 {:.2f}% 超过用户设定的单资产上限 {:.0f}%".format(item["name"], code, w * 100, cap))
        out["holdings"].append(item)

    out["hhi"] = _r(hhi, 4)
    out["effective_holdings"] = _r(1 / hhi, 2) if hhi else None
    out["max_weight_pct"] = _r(max((i["weight_pct"] or 0) for i in out["holdings"]), 2)
    out["single_asset_cap_pct"] = cap
    out["rebalance_band_pp"] = band
    out["cap_breaches"] = breaches
    out["cap_check"] = "已执行（用户提供上限 {:.0f}%）".format(cap) if cap is not None else "未执行（未提供单资产上限；核心宽基 ETF 请用目标权重管理集中度）"
    out["rebalance_alerts"] = deviations
    out["rebalance_needed"] = bool(deviations)
    out["note"] = "HHI 为权重平方和，越接近 1 越集中；有效持仓数 = 1 / HHI。HHI 只描述分散度不构成好坏判断，阈值均为可调整的纪律参数"
    return out


def correlations(returns):
    keys = list((returns or {}).keys())
    matrix = {}
    for k1 in keys:
        matrix[k1] = {}
        s1 = [_f(x) for x in returns[k1] if _f(x) is not None]
        for k2 in keys:
            s2 = [_f(x) for x in returns[k2] if _f(x) is not None]
            matrix[k1][k2] = _r(pearson(s1, s2), 3)
    pairs = []
    for i, k1 in enumerate(keys):
        for k2 in keys[i + 1:]:
            c = matrix[k1][k2]
            if c is not None and c >= 0.8:
                pairs.append("{} 与 {} 相关系数 {:.3f}：高度同涨同跌，应合并视为一笔风险暴露".format(k1, k2, c))
    return {
        "matrix": matrix,
        "high_correlation_pairs": pairs,
        "note": "Pearson 相关系数基于用户提供的收益率序列，样本过短时仅供参考",
    }


def render(result):
    lines = ["=== 指标测算 ===", "说明：全部数值依据用户提供的输入计算，不含任何内置市场数据", ""]
    if "financial" in result:
        f = result["financial"]
        lines.append("【财务比率】报告期 {} / 单位 {} / 币种 {}".format(f["period"], f["unit"], f["currency"]))
        labels = [
            ("yoy_revenue_pct", "营收同比 %"), ("qoq_revenue_pct", "营收环比 %"),
            ("yoy_net_profit_pct", "归母/净利同比 %"), ("gross_margin_pct", "毛利率 %"),
            ("net_margin_pct", "净利率 %"), ("cash_content_pct", "经营现金流/净利润 %"),
            ("receivable_to_revenue_pct", "应收/收入 %"), ("debt_ratio_pct", "资产负债率 %"),
            ("roe_pct", "ROE %"),
        ]
        for k, label in labels:
            lines.append("  {:<24} {}".format(label, "未提供" if f[k] is None else "{:.2f}".format(f[k])))
        for flag in f["flags"]:
            lines.append("  ! {}".format(flag))
        lines.append("")
    if "valuation" in result:
        v = result["valuation"]
        lines.append("【估值分位】{} / 样本 {} 个 / 区间 {}".format(v["label"], v["sample_size"], v["sample_range"]))
        lines.append("  当前 {} / 分位 {} / 最小 {} / 中位数 {} / 最大 {}".format(
            v["current_pe"], v["percentile_pct"], v["min"], v["median"], v["max"]))
        for flag in v["flags"]:
            lines.append("  ! {}".format(flag))
        lines.append("")
    if "portfolio" in result:
        p = result["portfolio"]
        lines.append("【组合】时点 {} / 合计 {:.2f}".format(p["as_of"], p.get("total_value") or 0))
        for h in p.get("holdings", []):
            lines.append("  {}（{}）{:>12.2f}  权重 {:.2f}%".format(h["name"], h["code"], h["value"], h["weight_pct"]))
        lines.append("  HHI {} / 有效持仓数 {} / 最大权重 {}%".format(p.get("hhi"), p.get("effective_holdings"), p.get("max_weight_pct")))
        lines.append("  是否触发再平衡：{}".format("是" if p.get("rebalance_needed") else "否"))
        for a in p.get("cap_breaches", []) + p.get("rebalance_alerts", []):
            lines.append("  ! {}".format(a))
        lines.append("")
    if "correlations" in result:
        c = result["correlations"]
        lines.append("【相关性矩阵】")
        keys = list(c["matrix"].keys())
        lines.append("  " + " " * 12 + " ".join("{:>10}".format(k[:10]) for k in keys))
        for k1 in keys:
            lines.append("  {:<12}".format(k1[:12]) + " ".join("{:>10}".format(str(c["matrix"][k1][k2])) for k2 in keys))
        for a in c["high_correlation_pairs"]:
            lines.append("  ! {}".format(a))
        lines.append("")
    lines.append("提示：阈值与分位仅为经验刻度；结论须结合一手来源、报告期口径与用户资金期限，不构成投资建议。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="财务 / 估值 / 组合指标计算器")
    ap.add_argument("--input", help="JSON 数据文件路径")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读 JSON")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    args = ap.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif args.stdin:
        data = json.load(sys.stdin)
    else:
        ap.error("需要 --input <json文件> 或 --stdin")

    result = {}
    if data.get("financial"):
        f = dict(data["financial"])
        f.setdefault("period", data.get("period", "未提供"))
        f.setdefault("unit", data.get("unit", "未提供"))
        f.setdefault("currency", data.get("currency", "未提供"))
        result["financial"] = financial(f)
    if data.get("valuation"):
        result["valuation"] = valuation(data["valuation"])
    if data.get("portfolio"):
        result["portfolio"] = portfolio(data["portfolio"])
    if data.get("returns"):
        result["correlations"] = correlations(data["returns"])
    if not result:
        ap.error("输入中未找到 financial / valuation / portfolio / returns 任一 section")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(result))


if __name__ == "__main__":
    main()
