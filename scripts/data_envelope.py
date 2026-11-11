#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据信封：让「来源 + 时点 + 口径 + 质量」随数据一起流转。

合规声明
--------
本模块改编自 Apache-2.0 项目
    kidulthhh-dotcom/china-stock-fund-analysis-skill
的 ``china-stock-fund-analysis/scripts/cn_finance/contracts.py``
（https://github.com/kidulthhh-dotcom/china-stock-fund-analysis-skill）。
原作者版权声明与许可证全文见本 Skill 的 ``licenses/Apache-2.0.txt``，
上游 NOTICE 见 ``licenses/NOTICE-upstream.txt``。

主要修改：
  1. 文档与注释改为中文，并按本 Skill 的「现金理财 → 场内配置」场景重写说明；
  2. 新增 ``market_status``（交易状态）与 ``notes`` 字段，用于承载盘前/盘中/盘后/休市与口径备注；
  3. ``schema_version`` 改为本 Skill 自有版本号，新增 ``to_dict`` 中对交易状态的输出；
  4. 增加 ``--demo`` / ``--self-test`` 命令行入口，便于离线验证；
  5. 简化为单文件、仅依赖 Python 标准库，不引入上游的 provider / quant 体系。

本模块不获取、不内置任何市场数据，也不联网；仅提供数据结构与工具函数。
原作者未参与本 Skill 的编写，亦未为本 Skill 背书。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any


class QualityFlag(str, Enum):
    """数据质量标记：非 ok 时必须在研报中显式说明。"""

    OK = "ok"
    PARTIAL = "partial"
    FALLBACK = "fallback"
    STALE = "stale"
    CONFLICTING = "conflicting"
    UNVERIFIABLE = "unverifiable"
    ERROR = "error"


@dataclass(frozen=True)
class SourceRef:
    """一次取数的来源引用。priority 建议用 primary / official / convenience / user_file。"""

    provider: str
    source_url: str | None = None
    source_path: str | None = None
    accessed_at: str = field(default_factory=lambda: date.today().isoformat())
    content_hash: str | None = None
    priority: str = "convenience"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_url": self.source_url,
            "source_path": self.source_path,
            "accessed_at": self.accessed_at,
            "content_hash": self.content_hash,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class ProviderAttempt:
    """取数链路中的一次尝试；失败与降级必须留痕。"""

    provider: str
    status: str
    started_at: str
    ended_at: str | None = None
    rows: int | None = None
    message: str | None = None

    @classmethod
    def start(cls, provider: str) -> "ProviderAttempt":
        return cls(provider=provider, status="started", started_at=utc_now())

    def finish(
        self,
        status: str,
        rows: int | None = None,
        message: str | None = None,
    ) -> "ProviderAttempt":
        return ProviderAttempt(
            provider=self.provider,
            status=status,
            started_at=self.started_at,
            ended_at=utc_now(),
            rows=rows,
            message=message,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "rows": self.rows,
            "message": self.message,
        }


@dataclass
class DataEnvelope:
    """一份带血缘的数据集合。

    request 里建议显式记录：标的、字段族、起止日期、复权口径、单位、币种；
    market_status 记录盘前 / 盘中 / 盘后 / 休市；notes 记录口径备注与限制。
    """

    request: dict[str, Any]
    rows: list[dict[str, Any]]
    provider_chain: list[ProviderAttempt]
    sources: list[SourceRef]
    data_cutoff: str | None = None
    quality_flags: list[QualityFlag] = field(default_factory=lambda: [QualityFlag.OK])
    warnings: list[str] = field(default_factory=list)
    market_status: str | None = None
    notes: list[str] = field(default_factory=list)
    schema_version: str = "1.1.0"
    generated_at: str = field(default_factory=lambda: utc_now())

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "request": self.request,
            "data_cutoff": self.data_cutoff,
            "market_status": self.market_status,
            "quality_flags": [flag.value for flag in self.quality_flags],
            "warnings": self.warnings,
            "notes": self.notes,
            "rows": self.rows,
            "sources": [source.to_dict() for source in self.sources],
            "provider_chain": [attempt.to_dict() for attempt in self.provider_chain],
        }
        payload["raw_hash"] = stable_hash(self.rows)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def utc_now() -> str:
    """ISO 8601 UTC 时间戳，精确到秒。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(value: Any) -> str:
    """对可 JSON 序列化对象生成稳定 SHA-256，用于内容比对与复现。"""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_cn_symbol(raw: str) -> str:
    """把境内 6 位代码规范化为 ``代码.交易所``；不判断产品类型、不校验代码真实存在。"""
    text = raw.strip().upper()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 6:
        raise ValueError("需要 6 位境内证券/基金代码，收到：{}".format(raw))
    if text.endswith(".SH") or text.startswith("SH") or digits.startswith(("5", "6", "9")):
        return "{}.SH".format(digits)
    if text.endswith(".SZ") or text.startswith("SZ") or digits.startswith(("0", "1", "2", "3")):
        return "{}.SZ".format(digits)
    if text.endswith(".BJ") or text.startswith("BJ") or digits.startswith(("4", "8")):
        return "{}.BJ".format(digits)
    return digits


def demo_envelope() -> DataEnvelope:
    """构造一份纯示例信封（全部为演示值，不是市场数据）。"""
    attempt = ProviderAttempt.start("示例：用户文件")
    attempt = attempt.finish("ok", rows=1, message="演示用，未读取任何真实文件")
    source = SourceRef(
        provider="示例：用户提供的持仓表",
        source_path="<示例文件>.csv",
        content_hash=stable_hash({"demo": True}),
        priority="user_file",
    )
    return DataEnvelope(
        request={
            "symbols": ["510300.SH"],
            "field_family": "portfolio_weight",
            "unit": "CNY",
            "adjustment": "not_applicable",
            "demo": True,
        },
        rows=[{"symbol_normalized": "510300.SH", "value": 0, "note": "示例值，不是行情"}],
        provider_chain=[attempt],
        sources=[source],
        data_cutoff="2026-11-10",
        market_status="休市（示例）",
        quality_flags=[QualityFlag.OK],
        warnings=["本信封仅用于演示结构，不含任何真实市场数据"],
        notes=["所有比例与阈值均为可调整的规划假设"],
    )


def self_test() -> dict[str, Any]:
    """离线契约自检，不联网、不读用户文件。"""
    checks: list[str] = []
    env = demo_envelope()
    payload = env.to_dict()
    assert payload["schema_version"] == "1.1.0"
    assert payload["quality_flags"] == ["ok"]
    assert len(payload["raw_hash"]) == 64
    checks.append("envelope_to_dict")
    assert json.loads(env.to_json())["rows"] == payload["rows"]
    checks.append("envelope_to_json")
    assert normalize_cn_symbol("510300") == "510300.SH"
    assert normalize_cn_symbol("sz159915") == "159915.SZ"
    assert normalize_cn_symbol("600519.SH") == "600519.SH"
    checks.append("symbol_normalization")
    try:
        normalize_cn_symbol("00700")
    except ValueError:
        checks.append("bad_symbol_rejected")
    else:
        raise AssertionError("5 位代码应被拒绝")
    attempt = ProviderAttempt.start("测试源").finish("fallback", rows=0, message="演示降级")
    assert attempt.status == "fallback" and attempt.ended_at is not None
    checks.append("provider_attempt")
    assert stable_hash({"b": 1, "a": 2}) == stable_hash({"a": 2, "b": 1})
    checks.append("stable_hash_order_independent")
    return {"status": "ok", "checks": checks, "schema_version": env.schema_version}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="输出一份示例数据信封 JSON（不含真实数据）")
    parser.add_argument("--self-test", action="store_true", help="运行离线契约自检")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
    elif args.demo:
        print(demo_envelope().to_json())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
