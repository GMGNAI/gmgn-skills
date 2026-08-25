#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""K 线形态判读 —— 从 GMGN 官方 OpenAPI 取 K 线，判形态，出分。

前置条件:
    npm install -g gmgn-cli   （一次即可；随后 gmgn-cli config 配好 API Key）

用法:
    python3 pattern.py <address> <chain> [resolution] [lang]

    address     代币合约地址。EVM 用 0x + 40 位十六进制；Solana 等用 base58
    chain       sol | bsc | base | eth | tron | ...
    resolution  1m 5m 15m 1h 4h 1d，默认 15m
    lang        zh | en，默认 zh

数据一律经由 gmgn-cli 取（本仓库 CLAUDE.md 的第一条硬性规则），所以这个脚本
**完全不接触 API Key，也不接触私钥** —— 鉴权、限流、输出消毒全部由 CLI 负责。
只用到 read-only 的 `market kline`，不碰任何交易命令。
零依赖，Python 3.9+ 标准库。

══ 这个脚本判的是「形态」，不是「会不会涨」══
它把六个可量化的指标（EMA 结构、20 根斜率、ATR 波动率、区间回撤、量比、
连阳连阴）合成一个 0-100 分，每一处加减分都会在输出里说明理由。
它不预测价格，也不给买卖建议 —— 形态是对已发生走势的描述。
"""
from __future__ import annotations

import json
import subprocess
import sys

VALID_RES = ("1s", "1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d")
# 官方支持的链。非 EVM 链的地址不是 0x 形态，校验规则不同。
NON_EVM = {"sol", "solana", "tron", "trx", "sui", "ton", "apt", "aptos"}


# ── i18n ──────────────────────────────────────────────────────────────────
T = {
    "zh": {
        "title": "K 线形态", "pattern": "形态", "score": "形态分",
        "slope": "斜率(20根)", "atr": "波动率 ATR", "volr": "量比",
        "dd": "区间回撤", "res": "粒度", "bars": "K 线根数",
        "signals": "逐项依据", "nodata": "K 线数据不足，无法判形态",
        "footer": ("形态是对已发生走势的描述，不预测价格，不构成投资建议。\n"
                   "数据源：GMGN 官方 OpenAPI /v1/market/token_kline（价格 K 线）。"),
        "range": "区间", "支撑": "支撑", "阻力": "阻力",
    },
    "en": {
        "title": "Price action", "pattern": "Pattern", "score": "Pattern score",
        "slope": "Slope (20 bars)", "atr": "Volatility ATR", "volr": "Volume ratio",
        "dd": "Drawdown in range", "res": "Resolution", "bars": "Bars",
        "signals": "Per-item evidence", "nodata": "Not enough candles to read a pattern",
        "footer": ("A pattern describes what already happened. It does not predict "
                   "price and is not investment advice.\n"
                   "Source: GMGN official OpenAPI /v1/market/token_kline (price candles)."),
        "range": "Range", "支撑": "Support", "阻力": "Resistance",
    },
}

PATTERN_EN = {
    "单边拉升": "Vertical run-up", "上升通道": "Uptrend channel",
    "破位下跌": "Breakdown", "高位派发/横盘": "Distribution at highs",
    "阴跌趋势": "Slow bleed", "底部横盘": "Basing at lows",
    "宽幅震荡": "Wide chop", "多头整理": "Bullish consolidation",
    "空头整理": "Bearish consolidation",
}




# ── 参数校验 ──────────────────────────────────────────────────────────────
def check_address(addr, chain):
    a = (addr or "").strip()
    if not a:
        die("缺少代币地址")
    if chain in NON_EVM:
        ok = 32 <= len(a) <= 44 and all(
            c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in a)
        if not ok:
            die("地址不像 %s 链的 base58 地址：%r" % (chain, a[:20]))
    else:
        ok = a.startswith("0x") and len(a) == 42 and all(
            c in "0123456789abcdefABCDEF" for c in a[2:])
        if not ok:
            die("地址不像 EVM 地址（0x + 40 位十六进制）：%r" % a[:24])
    return a


def check_chain(c):
    c = (c or "").strip().lower()
    if not c or not c.replace("-", "").isalnum():
        die("链名不合法：%r" % c)
    return c


def die(msg):
    sys.stderr.write("错误：%s\n" % msg)
    sys.exit(2)


# ── gmgn-cli 适配层 ──────────────────────────────────────────────────────────
# 本仓库的硬性规则（CLAUDE.md 第一条）：所有 GMGN 数据必须经由 gmgn-cli，
# 禁止 WebFetch / curl 直连任何 gmgn 域名。所以这里不自己发 HTTP，也**完全不碰
# API Key** —— 鉴权、限流、输出消毒全部由 CLI 负责。写法沿用
# skills/gmgn-holder-analysis/analyze.py 的 run_cli()。
def run_cli(args, timeout=30):
    try:
        r = subprocess.run(["gmgn-cli"] + args + ["--raw"],
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        die("gmgn-cli not found. Install it once with: npm install -g gmgn-cli")
    except subprocess.TimeoutExpired:
        die("gmgn-cli timed out after %ds" % timeout)
    if r.returncode != 0:
        die((r.stderr or "").strip() or "gmgn-cli exited %d" % r.returncode)
    try:
        return json.loads(r.stdout)
    except ValueError:
        die("gmgn-cli returned output that is not JSON")


def run_cli_opt(args, timeout=30):
    """Same, but a failure yields None instead of exiting.

    Used for the sources this skill can do without — losing one of them should
    degrade the report, not abort it.
    """
    try:
        r = subprocess.run(["gmgn-cli"] + args + ["--raw"],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def fetch_kline(addr, chain, resolution):
    d = run_cli(["market", "kline", "--chain", chain, "--address", addr,
                 "--resolution", resolution])
    lst = d if isinstance(d, list) else (d or {}).get("list")
    if not lst:
        die("No candles for %s on %s. Check the chain and the address." % (addr, chain))
    return lst


def normalise(raw):
    """官方的 time 是**毫秒**，volume 是**美元成交额**（amount 才是代币数量）。

    不换算毫秒的话，任何按秒算盘龄的逻辑都会把 K 线当成五万年后的数据。
    """
    rows = []
    for k in raw:
        try:
            t = float(k.get("time") or 0)
            rows.append({
                "t": int(t / 1000 if t > 1e12 else t),
                "open": float(k.get("open") or 0), "high": float(k.get("high") or 0),
                "low": float(k.get("low") or 0), "close": float(k.get("close") or 0),
                "volume": float(k.get("volume") or 0),
            })
        except (TypeError, ValueError):
            continue
    return [r for r in rows if r["close"] > 0]


# ── 指标 ──────────────────────────────────────────────────────────────────
def ema(vals, n):
    if not vals:
        return []
    k = 2.0 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def atr_pct(rows, n=14):
    if len(rows) < 2:
        return 0.0
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    trs = trs[-n:]
    last_close = rows[-1]["close"] or 1
    return (sum(trs) / len(trs)) / last_close if trs else 0.0


def slope_pct(closes, n=20):
    """最小二乘斜率，除以均值归一化成「这一段整体涨跌了百分之多少」。"""
    seg = closes[-n:]
    if len(seg) < 3:
        return 0.0
    m = len(seg)
    xbar = (m - 1) / 2.0
    ybar = sum(seg) / m
    num = sum((i - xbar) * (v - ybar) for i, v in enumerate(seg))
    den = sum((i - xbar) ** 2 for i in range(m)) or 1
    return (num / den) * m / (ybar or 1)


def classify(slope, dd, atr, trend_up, up_from_low):
    if slope > 0.25 and dd < 0.12:
        return "单边拉升"
    if slope > 0.08 and dd < 0.25:
        return "上升通道"
    if dd > 0.55 and slope < -0.1:
        return "破位下跌"
    if dd > 0.35 and abs(slope) < 0.08:
        return "高位派发/横盘"
    if slope < -0.2:
        return "阴跌趋势"
    if abs(slope) < 0.05 and atr < 0.05 and up_from_low < 0.2:
        return "底部横盘"
    if abs(slope) < 0.08 and atr > 0.08:
        return "宽幅震荡"
    return "多头整理" if trend_up else "空头整理"


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


# ── 判读 ──────────────────────────────────────────────────────────────────
def read(rows, resolution, lang):
    zh = lang == "zh"

    def s(c, e):
        return c if zh else e

    if len(rows) < 8:
        return {"score": 50, "pattern": None, "signals": [], "metrics": {},
                "note": T[lang]["nodata"]}

    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    last = rows[-1]
    e9, e21 = ema(closes, 9), ema(closes, 21)
    slope = slope_pct(closes, 20)
    atr = atr_pct(rows)
    win_high = max(r["high"] for r in rows)
    win_low = min(r["low"] for r in rows)
    dd = (win_high - last["close"]) / win_high if win_high else 0
    up_from_low = (last["close"] - win_low) / win_low if win_low else 0

    prev = vols[-21:-1]
    sma_v = sum(prev) / len(prev) if prev else 0
    vol_ratio = (vols[-1] / sma_v) if sma_v else 1.0

    greens = reds = 0
    for r in reversed(rows):
        if r["close"] >= r["open"]:
            greens += 1
        else:
            break
    for r in reversed(rows):
        if r["close"] < r["open"]:
            reds += 1
        else:
            break

    sig = []
    score = 50.0

    trend_up = e9[-1] > e21[-1]
    crossed = len(e9) > 2 and (e9[-2] <= e21[-2]) != (e9[-1] <= e21[-1])
    if trend_up:
        score += 12
        sig.append(("good", s("EMA9 在 EMA21 上方，短期多头结构",
                              "EMA9 above EMA21 — short-term bullish structure"), "+12"))
    else:
        score -= 12
        sig.append(("bad", s("EMA9 跌破 EMA21，短期空头结构",
                             "EMA9 below EMA21 — short-term bearish structure"), "-12"))
    if crossed:
        sig.append(("info", s("刚发生均线%s叉，形态转折点，注意假突破" % ("金" if trend_up else "死"),
                              "EMA just crossed %s — an inflection; watch for a fakeout"
                              % ("up" if trend_up else "down")), "0"))

    if slope > 0.15:
        score += 15
        sig.append(("good", s("近 20 根单边上行，斜率 +%.0f%%" % (slope * 100),
                              "Last 20 bars trend up, slope +%.0f%%" % (slope * 100)), "+15"))
    elif slope > 0.02:
        score += 6
        sig.append(("good", s("温和上行 +%.1f%%" % (slope * 100),
                              "Mild uptrend +%.1f%%" % (slope * 100)), "+6"))
    elif slope < -0.15:
        score -= 15
        sig.append(("bad", s("近 20 根单边下行 %.0f%%" % (slope * 100),
                             "Last 20 bars trend down %.0f%%" % (slope * 100)), "-15"))
    elif slope < -0.02:
        score -= 6
        sig.append(("warn", s("缓慢阴跌 %.1f%%" % (slope * 100),
                              "Slow bleed %.1f%%" % (slope * 100)), "-6"))
    else:
        sig.append(("info", s("横盘震荡，方向未定", "Sideways — no direction yet"), "0"))

    if vol_ratio > 3:
        up = last["close"] >= last["open"]
        score += 8 if up else -10
        sig.append(("good" if up else "bad",
                    s("最新一根放量 %.1fx —— %s" % (vol_ratio, "放量拉升" if up else "放量下砸"),
                      "Latest bar %.1fx volume — %s" % (vol_ratio,
                      "volume-backed push up" if up else "volume-backed dump")),
                    "+8" if up else "-10"))
    elif vol_ratio < 0.3:
        score -= 5
        sig.append(("warn", s("成交量萎缩至均量 %.0f%%，关注度流失" % (vol_ratio * 100),
                              "Volume shrank to %.0f%% of average — attention fading"
                              % (vol_ratio * 100)), "-5"))

    if dd > 0.6:
        score -= 15
        sig.append(("bad", s("较区间高点回撤 %.0f%%，接飞刀风险" % (dd * 100),
                             "Down %.0f%% from range high — catching-a-knife risk"
                             % (dd * 100)), "-15"))
    elif dd > 0.3:
        score -= 6
        sig.append(("warn", s("较区间高点回撤 %.0f%%" % (dd * 100),
                              "Down %.0f%% from range high" % (dd * 100)), "-6"))
    elif dd < 0.05:
        score += 8
        sig.append(("good", s("贴着区间高点运行", "Trading right at the range high"), "+8"))

    if atr > 0.15:
        sig.append(("warn", s("波动率极高 ATR %.1f%%，仓位要砍半" % (atr * 100),
                              "Very high volatility, ATR %.1f%% — size down" % (atr * 100)), "0"))
    elif atr < 0.02:
        sig.append(("info", s("波动率低 ATR %.1f%%" % (atr * 100),
                              "Low volatility, ATR %.1f%%" % (atr * 100)), "0"))

    if greens >= 5:
        sig.append(("warn", s("连续 %d 根阳线，短线超买，追高谨慎" % greens,
                              "%d green bars in a row — short-term overbought" % greens), "0"))
    if reds >= 5:
        sig.append(("warn", s("连续 %d 根阴线，下跌趋势未止跌" % reds,
                              "%d red bars in a row — downtrend not exhausted" % reds), "0"))

    if len(closes) > 40:
        p_now, p_prev = max(closes[-20:]), max(closes[-40:-20])
        v_now = sum(vols[-20:]) / 20
        v_prev = sum(vols[-40:-20]) / 20
        if p_now > p_prev * 1.02 and v_prev and v_now < v_prev * 0.7:
            score -= 10
            sig.append(("bad", s("量价背离：价格新高但成交量萎缩，上涨缺乏承接",
                                 "Divergence: new price high on shrinking volume — "
                                 "the move lacks participation"), "-10"))

    pattern = classify(slope, dd, atr, trend_up, up_from_low)
    return {
        "score": round(clamp(score)),
        "pattern": pattern if zh else PATTERN_EN.get(pattern, pattern),
        "signals": sig,
        "metrics": {"slope": slope, "atr": atr, "vol_ratio": vol_ratio,
                    "dd": dd, "support": win_low, "resistance": win_high,
                    "bars": len(rows)},
        "note": None,
    }


# ── 输出 ──────────────────────────────────────────────────────────────────
MARK = {"good": "✅", "warn": "⚠️ ", "bad": "🔴", "info": "·"}


def _w(text):
    """终端显示宽度。CJK 与全角标点占两列，用 len() 对齐中文会歪。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def pad(text, width):
    return text + " " * max(0, width - _w(text))


def render(res, addr, chain, resolution, lang):
    t = T[lang]
    out = []
    out.append("%s · %s" % (t["title"], chain.upper()))
    out.append(addr)
    out.append("─" * 62)
    if res["note"]:
        out.append(res["note"])
        out.append("")
        out.append(t["footer"])
        return "\n".join(out)

    m = res["metrics"]
    co = "：" if lang == "zh" else ": "
    out.append("%s %s" % (pad(t["pattern"] + co + res["pattern"], 34),
                          t["score"] + co + "%d / 100" % res["score"]))
    out.append("")
    out.append("%s %+.1f%%" % (pad(t["slope"], 18), m["slope"] * 100))
    out.append("%s %.1f%%" % (pad(t["atr"], 18), m["atr"] * 100))
    out.append("%s %.2fx" % (pad(t["volr"], 18), m["vol_ratio"]))
    out.append("%s %.0f%%" % (pad(t["dd"], 18), m["dd"] * 100))
    out.append("%s %s / %s" % (pad(t["range"], 18), fmt_price(m["support"]),
                               fmt_price(m["resistance"])))
    out.append("%s %s × %d" % (pad(t["bars"], 18), resolution, m["bars"]))
    out.append("")
    out.append("%s" % t["signals"])
    for level, text, delta in res["signals"]:
        d = "" if delta == "0" else "  (%s)" % delta
        out.append("  %s %s%s" % (MARK[level], text, d))
    out.append("")
    out.append("─" * 62)
    out.append(t["footer"])
    return "\n".join(out)


def fmt_price(v):
    if v is None:
        return "-"
    if v >= 1:
        return "%.4f" % v
    if v >= 0.0001:
        return "%.6f" % v
    return "%.3e" % v


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(__doc__ or "")
        sys.exit(2)
    chain = check_chain(sys.argv[2])
    addr = check_address(sys.argv[1], chain)
    resolution = sys.argv[3] if len(sys.argv) > 3 else "15m"
    lang = sys.argv[4] if len(sys.argv) > 4 else "zh"
    if resolution not in VALID_RES:
        die("粒度不支持：%r。可选 %s" % (resolution, " ".join(VALID_RES)))
    if lang not in ("zh", "en"):
        lang = "zh"

    rows = normalise(fetch_kline(addr, chain, resolution))
    print(render(read(rows, resolution, lang), addr, chain, resolution, lang))


if __name__ == "__main__":
    main()
