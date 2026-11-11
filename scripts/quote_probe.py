#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A 股 / 港股 / 美股公开行情快照探针（可选能力，默认不运行）。

设计边界
--------
* 仅 Python 标准库、不写本地文件、不安装依赖、不内置任何市场数据。
* **只在用户明确询问「现价 / 最新价」时使用**；否则走 SKILL.md 的检索路由。
* 只向公开非登录端点发送标的代码，不发送持仓、金额、账户或任何个人信息。
* 返回快照而非逐笔行情；休市时为最近一次收盘。交易状态、字段含义、限频策略
  与端点可用性均要求**运行时核实**，脚本本身不判断盘前/盘中/盘后。
* 解析保守：只取名称、代码、最新价、昨收、行情时间与币种，涨跌幅由前两者现算；
  不解析买卖档位、成交额、复权或净值字段，避免字段位置变动导致误读。
* 端点失败时返回 ``quality_flags=["unverifiable"]`` 与空 rows，由上层降级到
  检索路由；**禁止**用记忆中的价格补位。

三市场差异（2026-11 实测）
--------------------------
* A 股：代码前缀 ``sh`` / ``sz``；行情时间为载荷中的 14 位 ``YYYYMMDDhhmmss``。
* 港股：代码前缀 ``hk`` + 5 位，如 ``hk00700``；``parts[30]`` 为 ``YYYY/MM/DD hh:mm:ss``。
* 美股：代码前缀 ``us`` + ticker，如 ``usAAPL``；``parts[30]`` 为 ``YYYY-MM-DD hh:mm:ss``。
* 币种：港股 ``parts[75]``、美股 ``parts[35]``；取不到时按市场回退 HKD / USD。
* 三市场共用同一 ``~`` 分隔载荷，价格与昨收分别在 ``parts[3]`` / ``parts[4]``。

来源与许可
----------
实现为本 Skill 独立编写。公开端点域名、A 股/ETF/港股/美股代码位数规则等
**事实性信息**参考自 ``asfamilybank/stock-query`` 的 README / SKILL.md。该仓库
声明 MIT 但 GitHub API ``license`` 为 null 且无 LICENSE 文件，因此本脚本
**未使用其任何代码**，详见 ``THIRD_PARTY_NOTICES.md``。

用法::

    python quote_probe.py --codes 510300 159915
    python quote_probe.py --codes hk00700 usAAPL
    python quote_probe.py --codes sh000001 --provider sina --timeout 8
    python quote_probe.py --self-test

退出码：0 成功（含 partial）；2 全部来源失败或入参错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from typing import Any

from data_envelope import (
    DataEnvelope,
    ProviderAttempt,
    QualityFlag,
    SourceRef,
    normalize_cn_symbol,
    stable_hash,
)

TENCENT_URL = "https://qt.gtimg.cn/q="
SINA_URL = "https://hq.sinajs.cn/list="
USER_AGENT = "personal-investing-copilot/1.2.1 (public quote snapshot; research only)"

# 000001 在 A 股语境下既可能是上证指数也可能是平安银行，必须提示歧义。
AMBIGUOUS_CODES = {"000001"}

DISCLAIMER = "仅为公开接口行情快照，非逐笔实时行情，不构成投资建议；下单前以券商与交易所信息为准。"


def to_venue_symbol(raw: str) -> tuple[str, str, str]:
    """把用户输入规范化为 (端点代码, 标准代码, 币种)。

    支持：``510300`` / ``sh510300`` / ``510300.SH``；
    ``hk00700`` / ``00700.HK`` / 5 位裸代码 ``00700``；``usAAPL`` / ``AAPL.US`` / 裸 ticker ``AAPL``。
    不判断产品类型，也不校验代码真实存在；北交所暂不覆盖。
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("标的代码为空")

    upper = text.upper()

    # 港股：hk 前缀 / .HK 后缀 / 5 位纯数字（A 股恒为 6 位，不会冲突）
    if upper.startswith("HK") or upper.endswith(".HK") or re.fullmatch(r"\d{5}", text):
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) != 5:
            raise ValueError("港股需要 5 位代码，收到：{}".format(raw))
        return "hk" + digits, digits + ".HK", "HKD"

    # 美股：us 前缀或 .US 后缀
    if upper.startswith("US") or upper.endswith(".US"):
        ticker = text[2:] if upper.startswith("US") else text[:-3]
        ticker = ticker.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", ticker):
            raise ValueError("美股 ticker 格式不合法：{}".format(raw))
        return "us" + ticker, ticker + ".US", "USD"

    # 裸 ticker（无数字、含字母）默认按美股处理
    if not any(ch.isdigit() for ch in text) and re.fullmatch(r"[A-Za-z][A-Za-z0-9.\-]{0,9}", text):
        ticker = text.upper()
        return "us" + ticker, ticker + ".US", "USD"

    normalized = normalize_cn_symbol(raw)
    code, _, venue = normalized.partition(".")
    if venue == "SH":
        return "sh" + code, normalized, "CNY"
    if venue == "SZ":
        return "sz" + code, normalized, "CNY"
    raise ValueError("暂不覆盖该代码所属市场（北交所等）：{}，请改用检索路由".format(raw))


def _http_get(url: str, timeout: float, referer: str | None = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - 公开只读端点
        data = resp.read()
    return data.decode("gbk", errors="replace")


def _find_timestamp(parts: list[str]) -> str | None:
    for item in parts:
        if len(item) == 14 and item.isdigit():
            return "{}-{}-{} {}:{}:{}".format(
                item[0:4], item[4:6], item[6:8], item[8:10], item[10:12], item[12:14]
            )
    return None


def _timestamp(parts: list[str], venue_code: str) -> str | None:
    """按市场解析行情时间：港股/美股在 parts[30]，A 股在 14 位数字串。

    港股返回 ``YYYY/MM/DD hh:mm:ss``，统一把斜杠换成连字符，保证 ``data_cutoff``
    与 A 股同格式、可比较。
    """
    if venue_code.startswith(("hk", "us")):
        if len(parts) > 30:
            candidate = parts[30].strip()
            if candidate and ":" in candidate:
                return candidate.replace("/", "-")
        return None
    return _find_timestamp(parts)


def _currency(parts: list[str], venue_code: str, default: str) -> str:
    """按市场读取币种字段，取不到或不在白名单时回退默认值。"""
    if venue_code.startswith("hk"):
        index = 75
    elif venue_code.startswith("us"):
        index = 35
    else:
        return "CNY"
    if len(parts) > index:
        candidate = parts[index].strip().upper()
        if candidate == "RMB":
            candidate = "CNY"
        if candidate in ("CNY", "HKD", "USD"):
            return candidate
    return default


def _row(
    symbol_normalized: str,
    name: str,
    price: float,
    prev_close: float | None,
    as_of: str | None,
    provider: str,
    source_url: str,
    currency: str,
) -> dict[str, Any]:
    change_pct = None
    if prev_close not in (None, 0) and price is not None:
        change_pct = round((price / prev_close - 1) * 100, 4)
    return {
        "symbol_normalized": symbol_normalized,
        "name": name,
        "price": price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "currency": currency,
        "as_of": as_of,
        "provider": provider,
        "source_url": source_url,
        "quality_flag": "ok" if as_of else "partial",
        "note": "快照；交易状态与字段口径需运行时核实",
    }


def fetch_tencent(
    symbols: list[tuple[str, str, str]], timeout: float
) -> tuple[str, list[dict[str, Any]]]:
    url = TENCENT_URL + ",".join(item[0] for item in symbols)
    text = _http_get(url, timeout)
    lookup = {item[0]: item for item in symbols}
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        venue_code = key.strip().removeprefix("v_")
        payload = value.strip().strip('";')
        parts = payload.split("~")
        if len(parts) < 6 or venue_code not in lookup:
            continue
        try:
            price = float(parts[3])
            prev_close = float(parts[4]) if parts[4] else None
        except (ValueError, IndexError):
            continue
        item = lookup[venue_code]
        rows.append(
            _row(
                item[1],
                parts[1].strip(),
                price,
                prev_close,
                _timestamp(parts, venue_code),
                "腾讯财经公开行情接口",
                url,
                _currency(parts, venue_code, item[2]),
            )
        )
    return url, rows


def fetch_sina(
    symbols: list[tuple[str, str, str]], timeout: float
) -> tuple[str, list[dict[str, Any]]]:
    cn_symbols = [item for item in symbols if item[0].startswith(("sh", "sz"))]
    if not cn_symbols:
        raise ValueError("新浪端点仅覆盖 A 股，当前请求不含 A 股代码")
    url = SINA_URL + ",".join(item[0] for item in cn_symbols)
    text = _http_get(url, timeout, referer="https://finance.sina.com.cn")
    lookup = {item[0]: item for item in cn_symbols}
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if '"' not in line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        venue_code = key.strip().removeprefix("var hq_str_")
        payload = value.strip().strip('";')
        parts = payload.split(",")
        if len(parts) < 32 or venue_code not in lookup:
            continue
        try:
            price = float(parts[3])
            prev_close = float(parts[2]) if parts[2] else None
        except (ValueError, IndexError):
            continue
        as_of = "{} {}".format(parts[30], parts[31]).strip()
        rows.append(
            _row(
                lookup[venue_code][1],
                parts[0].strip(),
                price,
                prev_close,
                as_of or None,
                "新浪财经公开行情接口",
                url,
                "CNY",
            )
        )
    return url, rows


FETCHERS = {
    "tencent": fetch_tencent,
    "sina": fetch_sina,
}


def probe(codes: list[str], provider: str = "auto", timeout: float = 8.0) -> DataEnvelope:
    symbols: list[tuple[str, str, str]] = []
    errors: list[str] = []
    invalid_codes: list[str] = []
    for raw in codes:
        try:
            symbols.append(to_venue_symbol(raw))
        except ValueError as exc:
            invalid_codes.append(raw)
            errors.append(str(exc))

    # 降级循环会裁剪 symbols，市场集合与期望标的数必须基于完整请求预先计算。
    symbols_all = list(symbols)
    markets_all = sorted(
        {("HK" if item[0].startswith("hk") else "US" if item[0].startswith("us") else "CN") for item in symbols_all}
    ) or ["CN"]
    expected_count = len({item[1] for item in symbols_all})

    warnings = [
        DISCLAIMER,
        "脚本不判断交易状态；休市时该快照为最近一次收盘价，需人工确认。",
        "港股 / 美股与 A 股共用同一公开端点，但字段位置不同，解析按市场分支，详见 references/data-sources.md 第 7 节。",
    ]
    if len(markets_all) > 1:
        warnings.append(
            "跨市场请求：A 股 / 港股时间戳为当地交易时间，美股通常为美东时间，三者字符串不可直接比较；"
            "data_cutoff 仅按字符串排序展示，不代表同一时点的可比数据。研报须逐条标注市场与时点，"
            "时区以运行时核实为准；A 股「红涨绿跌」颜色约定不适用于境外市场。"
        )
    for raw in codes:
        if "".join(ch for ch in raw if ch.isdigit()) in AMBIGUOUS_CODES and not raw.lower().startswith(("sh", "sz")):
            warnings.append("代码 000001 存在歧义（上证指数 / 平安银行），请显式写 sh000001 或 sz000001。")
            break

    chain: list[ProviderAttempt] = []
    sources: list[SourceRef] = []
    merged: dict[str, dict[str, Any]] = {}
    order = ["tencent", "sina"] if provider == "auto" else [provider]

    for name in order:
        if not symbols:
            break
        attempt = ProviderAttempt.start(name)
        fetcher = FETCHERS.get(name)
        if fetcher is None:
            attempt = attempt.finish("error", message="未知数据源")
            chain.append(attempt)
            continue
        try:
            url, rows = fetcher(symbols, timeout)
            for row in rows:
                merged.setdefault(row["symbol_normalized"], row)
            sources.append(
                SourceRef(
                    provider="{} 公开行情快照".format(name),
                    source_url=url,
                    content_hash=stable_hash(rows),
                    priority="convenience",
                )
            )
            attempt = attempt.finish("ok" if rows else "empty", rows=len(rows))
            chain.append(attempt)
            if provider == "auto":
                missing = [item for item in symbols if item[1] not in merged]
                if not missing:
                    break
                symbols = missing
        except Exception as exc:  # 网络/解析失败必须留痕并降级，不得静默
            attempt = attempt.finish("error", message="{}: {}".format(type(exc).__name__, exc))
            chain.append(attempt)
            errors.append("{} 取数失败：{}".format(name, exc))

    rows_out = list(merged.values())
    # 按成功规范化的唯一标的计数：重复代码或不合法代码不应误报「部分标的未取到」。
    expected = expected_count
    if not rows_out:
        flags = [QualityFlag.UNVERIFIABLE]
        warnings.append("全部公开端点均未返回可用数据；请改用检索路由，禁止凭记忆填写价格。")
    elif invalid_codes or len(rows_out) < expected or any(r["quality_flag"] != "ok" for r in rows_out):
        flags = [QualityFlag.PARTIAL]
        warnings.append("部分标的或字段未取到，结论范围需相应缩小。")
        if invalid_codes:
            warnings.append(
                "以下入参未按代码规则识别，已跳过：{}；请改写为受支持格式或改用检索路由。".format(
                    "、".join(invalid_codes)
                )
            )
    else:
        flags = [QualityFlag.OK]
    warnings.extend(errors)

    return DataEnvelope(
        request={
            "codes": codes,
            "provider_mode": provider,
            "timeout_seconds": timeout,
            "network_scope": "仅公开只读行情端点；请求只含标的代码，不含任何用户数据",
            "field_family": "quote_snapshot",
            "markets": markets_all,
        },
        rows=rows_out,
        provider_chain=chain,
        sources=sources,
        data_cutoff=max((r["as_of"] for r in rows_out if r.get("as_of")), default=None),
        quality_flags=flags,
        warnings=warnings,
        market_status="需运行时核实（脚本仅返回快照时点）",
        notes=[
            "A 股习惯：涨红跌绿；本脚本输出数值，颜色由上层渲染",
            "端点字段与限频策略可能变化，务必运行时核实",
            "本脚本不做历史 K 线、场外基金估值、复权计算，也不下单",
        ],
    )


def self_test() -> dict[str, Any]:
    """离线自检：代码规范化、信封结构与降级分支，不联网。"""
    checks: list[str] = []
    assert to_venue_symbol("510300") == ("sh510300", "510300.SH", "CNY")
    assert to_venue_symbol("sz159915") == ("sz159915", "159915.SZ", "CNY")
    assert to_venue_symbol("sh000001") == ("sh000001", "000001.SH", "CNY")
    checks.append("symbol_mapping_cn")
    assert to_venue_symbol("hk00700") == ("hk00700", "00700.HK", "HKD")
    assert to_venue_symbol("00700.HK") == ("hk00700", "00700.HK", "HKD")
    assert to_venue_symbol("00700") == ("hk00700", "00700.HK", "HKD")
    checks.append("symbol_mapping_hk")
    assert to_venue_symbol("usAAPL") == ("usAAPL", "AAPL.US", "USD")
    assert to_venue_symbol("AAPL.US") == ("usAAPL", "AAPL.US", "USD")
    assert to_venue_symbol("AAPL") == ("usAAPL", "AAPL.US", "USD")
    checks.append("symbol_mapping_us")
    try:
        to_venue_symbol("830001")
    except ValueError:
        checks.append("unsupported_market_rejected")
    else:
        raise AssertionError("北交所代码应被拒绝")
    try:
        to_venue_symbol("hk0700")
    except ValueError:
        checks.append("bad_hk_code_rejected")
    else:
        raise AssertionError("4 位港股代码应被拒绝")
    env = probe(["510300"], provider="tencent", timeout=0.001)
    assert env.quality_flags == [QualityFlag.UNVERIFIABLE]
    assert env.rows == [] and env.provider_chain
    assert env.provider_chain[0].status == "error"
    checks.append("network_failure_is_visible")
    payload = env.to_dict()
    assert payload["request"]["network_scope"] and payload["warnings"]
    checks.append("envelope_contract")
    # 混合市场 + 全部来源失败：市场集合、时区提示不能被降级循环裁剪掉。
    mixed = probe(["510300", "hk00700", "AAPL"], provider="tencent", timeout=0.001).to_dict()
    assert mixed["request"]["markets"] == ["CN", "HK", "US"]
    assert any("跨市场请求" in w for w in mixed["warnings"])
    checks.append("mixed_market_envelope_preserved")

    # 用假数据源验证质量标记：入参被跳过必须降级，重复代码不应误报。
    original = FETCHERS["tencent"]

    def _fake(syms: list[tuple[str, str, str]], timeout: float) -> tuple[str, list[dict[str, Any]]]:
        url = "https://example.invalid/q="
        return url, [
            _row(s[1], "模拟标的", 1.0, 1.0, "2026-11-10 15:00:00", "离线测试", url, s[2]) for s in syms
        ]

    FETCHERS["tencent"] = _fake
    try:
        rejected = probe(["510300", "830001"], provider="tencent", timeout=0.001)
        assert rejected.quality_flags == [QualityFlag.PARTIAL]
        assert any("已跳过" in w for w in rejected.warnings)
        checks.append("invalid_input_forces_partial")
        duplicate = probe(["510300", "510300"], provider="tencent", timeout=0.001)
        assert duplicate.quality_flags == [QualityFlag.OK]
        checks.append("duplicate_input_is_ok")
    finally:
        FETCHERS["tencent"] = original
    return {"status": "ok", "checks": checks, "note": "离线自检，质量标记分支用假数据源验证，未发起真实网络请求"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--codes", nargs="+", help="A 股 6 位 / 港股 hk+5 位 / 美股 ticker")
    parser.add_argument("--provider", choices=["auto", "tencent", "sina"], default="auto")
    parser.add_argument("--timeout", type=float, default=8.0, help="单次请求超时秒数，默认 8")
    parser.add_argument("--self-test", action="store_true", help="离线自检，不联网")
    args = parser.parse_args()

    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return
    if not args.codes:
        parser.error("需要 --codes（或使用 --self-test）")
    env = probe(args.codes, provider=args.provider, timeout=args.timeout)
    print(env.to_json())
    if env.quality_flags == [QualityFlag.UNVERIFIABLE]:
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
