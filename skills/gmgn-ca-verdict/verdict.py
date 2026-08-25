#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""CA 综合尽调评分 —— 三项确定性技能合成一个 0-100 分，每一处扣分都说明理由。

前置条件:
    npm install -g gmgn-cli   （一次即可；随后 gmgn-cli config 配好 API Key）

用法:
    python3 verdict.py <address> <chain> [lang]

数据一律经由 gmgn-cli 取（本仓库 CLAUDE.md 的第一条硬性规则），所以这个脚本
**完全不接触 API Key，也不接触私钥**。只用到三条 read-only 命令：
`token info` / `token security` / `market kline`，不碰任何交易命令。
零依赖，Python 3.9+ 标准库。

══ 这个脚本最重要的一条规则：缺失数据绝不算好消息 ══
链上数据经常缺字段。天真的写法是 f(None) -> 0，于是「Dev 持仓 0%」和「狙击占比
0%」这两个**查都没查到**的项会被读成正面信号，打出「Dev 已清仓」「狙击盘已出清」。
比标成「数据缺失」更糟：它让一个完全没检查过的盘看起来是干净的 —— 实测中一个
未经检查的代币可以拿到满分 100。

所以：
  · 任何正面信号都要先用 has() 确认字段真的存在
  · 蜜罐检测拿不到时，综合分**封顶 59**，并在结论里直说「关键项未查到」
  · 缺失项会逐条列出来，而不是悄悄按 0 处理
"""
from __future__ import annotations

import json
import subprocess
import sys

NON_EVM = {"sol", "solana", "tron", "trx", "sui", "ton", "apt", "aptos"}

# 权重。催化剂与 X 叙事不在本包内（见 README），composite 只对**实际拿到的**技能
# 归一化，所以缺项不会把分数拉低，只是让剩下的项权重相应放大。
WEIGHTS = {"ca_audit": 0.34, "holders": 0.22, "kline": 0.15}


# ── 小工具 ────────────────────────────────────────────────────────────────
def f(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def has(*pairs):
    """字段**是否真的存在**。见模块开头那段说明 —— 这是整个包的地基。"""
    return any(src and src.get(k) not in (None, "") for src, k in pairs)


def tri(v):
    """三态布尔：True / False / None（缺失）。

    官方混用了两种形状：`is_open_source` 是 bool，`open_source` 是 0/1。
    而字段缺失时是 None。用真值判断会把 None 和 False 混为一谈 —— 「没查到是否
    开源」和「确认未开源」是完全不同的两件事，前者不该扣分，后者该扣。
    """
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("1", "true", "yes"):
        return True
    if s in ("0", "false", "no"):
        return False
    return None


def pct(x, d=1):
    return "%.*f%%" % (d, f(x) * 100)


def usd(v):
    v = f(v)
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            return "$%.2f%s" % (v / div, unit)
    return "$%.2f" % v


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def die(msg):
    sys.stderr.write("错误：%s\n" % msg)
    sys.exit(2)


# ── gmgn-cli 适配层 ──────────────────────────────────────────────────────────
# 本仓库的硬性规则（CLAUDE.md 第一条）：所有 GMGN 数据必须经由 gmgn-cli，
# 禁止直连任何 gmgn 域名。所以这里不自己发 HTTP，也**完全不碰 API Key** ——
# 鉴权、限流、输出消毒全部由 CLI 负责。写法沿用 gmgn-holder-analysis/analyze.py。
def run_cli(args, timeout=30, optional=False):
    try:
        r = subprocess.run(["gmgn-cli"] + args + ["--raw"],
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        die("gmgn-cli not found. Install it once with: npm install -g gmgn-cli")
    except subprocess.TimeoutExpired:
        if optional:
            return None
        die("gmgn-cli timed out after %ds" % timeout)
    if r.returncode != 0:
        if optional:
            return None
        die((r.stderr or "").strip() or "gmgn-cli exited %d" % r.returncode)
    try:
        return json.loads(r.stdout)
    except ValueError:
        if optional:
            return None
        die("gmgn-cli returned output that is not JSON")


# ── 技能 ① 合约安全 ───────────────────────────────────────────────────────
def skill_ca(info, sec, L):
    stat = info.get("stat") or {}
    dev = info.get("dev") or {}
    pool = info.get("pool") or {}
    score = 100.0
    sig, unknown = [], []

    # ── 蜜罐 ──
    # 一票否决项，也是「未知就封顶」的那一项。
    #
    # 但这里有一类真实存在的**假阳性**：币股 / RWA 这类代币带有合规转账限制
    # （白名单、转账钩子），蜜罐模拟器跑一次卖出失败就把它标成蜜罐。实测：
    #   SPYB  is_honeypot=True，但 24h 有 15,660 笔卖出、卖出额 $4.49M
    #   QQQB  is_honeypot=True，但 24h 有 128,200 笔卖出、卖出额 $34.18M
    # 一个卖不出去的币不可能成交 12.8 万笔卖单。这两个币还都是
    # privileges=[] flags=[] 买卖税 0 —— 真蜜罐必须有个特权机制才拦得住卖出。
    #
    # 处理方式**不是把它洗成 False**。数据只证明了「能卖」，没证明「合约里不存在
    # 转账限制」—— 限制可能只在特定条件下触发。所以降级成**未知**，交给既有的
    # 「关键项未查到 -> 封顶 59」机制。这比新造一条放行逻辑安全得多：
    # 最坏情况是一个真蜜罐拿到 59 分而不是 8 分，而不是拿到 90 分。
    hp = tri(sec.get("is_honeypot"))
    if hp is None:
        hp = tri(sec.get("honeypot"))

    contradiction = None
    if hp is True:
        px = info.get("price") or {}
        sells = f(px.get("sells_24h"))
        buys = f(px.get("buys_24h"))
        sell_v = f(px.get("sell_volume_24h"))
        buy_v = f(px.get("buy_volume_24h"))
        ratio = (sell_v / buy_v) if buy_v else 0.0
        no_priv = (not sec.get("privileges")) and (not sec.get("flags"))
        no_tax = max(f(sec.get("buy_tax")), f(sec.get("sell_tax"))) <= 0.001
        # 门槛定得高，是为了不让真蜜罐靠「几笔白名单地址的卖出」蒙混过去。
        # 卖出额与买入额同量级（0.3~3）才算真实双向市场 —— 蜜罐是买入远大于卖出。
        if (sells >= 500 and sell_v >= 100000 and 0.3 <= ratio <= 3.0
                and no_priv and no_tax):
            contradiction = {"sells": int(sells), "buys": int(buys),
                             "sell_v": sell_v, "ratio": ratio}

    if contradiction:
        hp = None   # 降级为未知，触发下面的 unknown -> 封顶 59
        score -= 10
        sig.append(("warn",
                    L("蜜罐标记与实际成交矛盾：24h 有 %s 笔卖出、卖出额 %s"
                      % ("{:,}".format(contradiction["sells"]), usd(contradiction["sell_v"])),
                      "Honeypot flag contradicted by actual trading: %s sells worth %s in 24h"
                      % ("{:,}".format(contradiction["sells"]), usd(contradiction["sell_v"]))),
                    L("常见于币股/RWA 这类带合规转账限制的代币，模拟器卖出失败即误判；"
                      "但仍不能证明合约无转账限制，按未知处理",
                      "typical of tokenized-equity / RWA tokens with compliance transfer "
                      "rules — the simulator's failed sell is a false positive; still not "
                      "proof the contract is unrestricted, so treated as unknown")))
    if hp is True:
        score = 0.0
        sig.append(("bad", L("蜜罐合约：买得进卖不出", "Honeypot: you can buy but not sell"),
                    L("直接规避", "avoid")))
    elif hp is None:
        unknown.append(L("蜜罐检测", "honeypot check"))

    # 税
    bt, st = f(sec.get("buy_tax")), f(sec.get("sell_tax"))
    mx = max(bt, st)
    if has((sec, "buy_tax"), (sec, "sell_tax")):
        if mx > 0.10:
            score -= 25
            sig.append(("bad", L("交易税过高 %s" % pct(mx), "Tax too high %s" % pct(mx)),
                        L("高税会吃掉波段利润", "eats swing profit")))
        elif mx > 0.05:
            score -= 10
            sig.append(("warn", L("交易税偏高 %s" % pct(mx), "Tax elevated %s" % pct(mx)), ""))
    else:
        unknown.append(L("买卖税", "buy/sell tax"))

    # 开源
    os_ = tri(sec.get("is_open_source"))
    if os_ is None:
        os_ = tri(sec.get("open_source"))
    if os_ is False:
        score -= 15
        sig.append(("bad", L("合约未开源", "Contract is not open source"),
                    L("无法验证逻辑，可能留有后门", "logic cannot be verified")))
    elif os_ is True:
        sig.append(("good", L("合约已开源", "Contract is open source"), ""))
    else:
        unknown.append(L("是否开源", "open-source status"))

    # 弃权
    rn = tri(sec.get("is_renounced"))
    if rn is None:
        rn = tri(sec.get("renounced"))
    if rn is True:
        sig.append(("good", L("已弃权（无增发/管理权限）", "Ownership renounced"), ""))
    elif rn is False:
        score -= 8
        sig.append(("warn", L("合约权限未弃权", "Ownership not renounced"),
                    L("dev 仍可能修改参数", "dev can still change parameters")))
    else:
        unknown.append(L("权限弃权状态", "renounce status"))

    # ── LP 锁定/销毁 ──
    # 这一段踩过坑，实测记录见 fields.md。真实结构是：
    #   lock_summary.lock_detail = [{percent, pool, is_blackhole}, ...]
    #     is_blackhole=true  -> 打进黑洞地址，即**已销毁**
    #     is_blackhole=false -> 第三方锁仓（pool 形如 "3rd_locked"）
    #   lock_summary.lock_percent 恒为 "0"，**不要用它**
    #   burn_status 在 security 里是空串（在 market/rank 里才是 "yes"）
    # 早先一版读 lock_percent，给一个 LP 已销毁 95% 的币报了「存在撤池风险」——
    # 正是这个包声称要避免的那类错误。
    ls = sec.get("lock_summary") or {}
    detail = ls.get("lock_detail")
    burned = locked = 0.0
    if isinstance(detail, list) and detail:
        for d in detail:
            p_ = f((d or {}).get("percent"))
            if (d or {}).get("is_blackhole"):
                burned += p_
            else:
                locked += p_
    # 兜底：security 没给 detail 时，看 burn_status / burn_ratio（market/rank 的形状）
    burn_s = str(sec.get("burn_status") or "").strip().lower()
    if burn_s in ("burn", "burnt", "yes", "true"):
        burned = max(burned, 1.0)
    burned = max(burned, f(sec.get("burn_ratio")))
    if not isinstance(detail, list) and sec.get("lock_percent") is not None:
        locked = max(locked, f(sec.get("lock_percent")))

    secured = burned + locked
    if isinstance(detail, list) or has((sec, "burn_status"), (sec, "burn_ratio"),
                                       (sec, "lock_percent")):
        if burned > 0.9:
            sig.append(("good", L("LP 已销毁 %s" % pct(burned, 0),
                                  "LP burned %s" % pct(burned, 0)), ""))
        elif locked > 0.9:
            sig.append(("good", L("LP 已锁定 %s" % pct(locked, 0),
                                  "LP locked %s" % pct(locked, 0)), ""))
        elif secured > 0.5:
            score -= 4
            sig.append(("warn", L("LP 仅部分锁定/销毁（%s）" % pct(secured, 0),
                                  "LP only partly secured (%s)" % pct(secured, 0)), ""))
        else:
            score -= 12
            sig.append(("bad", L("LP 未锁定也未销毁（%s）" % pct(secured, 0),
                                 "LP neither locked nor burned (%s)" % pct(secured, 0)),
                        L("dev 可随时撤池", "the dev can pull the pool at any time")))
    else:
        unknown.append(L("LP 锁定状态", "LP lock status"))

    # 流动性
    liq = f(pool.get("liquidity") or info.get("liquidity"))
    init = f(pool.get("initial_liquidity"))
    if liq:
        if liq < 10000:
            score -= 15
            sig.append(("bad", L("流动性过浅 %s" % usd(liq), "Liquidity very thin %s" % usd(liq)),
                        L("大单滑点极高，出货困难", "high slippage, hard to exit")))
        elif liq < 50000:
            score -= 6
            sig.append(("warn", L("流动性偏浅 %s" % usd(liq), "Liquidity thin %s" % usd(liq)), ""))
        if init and liq < init * 0.5:
            score -= 10
            sig.append(("bad", L("池子较开盘缩水 %s" % pct(1 - liq / init, 0),
                                 "Pool shrank %s from launch" % pct(1 - liq / init, 0)),
                        L("有抽水迹象", "signs of draining")))
    else:
        unknown.append(L("流动性", "liquidity"))

    # Dev 历史与社媒
    on_lp = bool(info.get("launchpad") or info.get("launchpad_platform"))
    created = f(stat.get("creator_created_count"))
    if created > 5 and not on_lp:
        score -= 8
        sig.append(("warn", L("Dev 已发过 %d 个币" % int(created),
                              "Dev has launched %d tokens" % int(created)),
                    L("批量发币工作室", "token mill")))
    if len(dev.get("twitter_name_change_history") or []) > 0:
        score -= 15
        sig.append(("bad", L("推特账号改过名", "The X account was renamed"),
                    L("老号改名蹭叙事的经典套路", "classic narrative-squatting move")))
    if f(dev.get("twitter_del_post_token_count")) > 0:
        score -= 10
        sig.append(("warn", L("项目方推文有删除记录", "The project has deleted posts"), ""))
    if f(dev.get("twitter_create_token_count")) > 1:
        score -= 8
        sig.append(("warn", L("同一推特账号发过多个币",
                              "The same X account launched several tokens"), ""))
    if f(info.get("image_dup_count")) > 0:
        score -= 8
        sig.append(("warn", L("头像/图片与其他代币重复",
                              "Logo is a duplicate of another token"), ""))
    if tri(dev.get("cto_flag")) is True:
        sig.append(("info", L("社区接管（CTO）项目", "Community takeover (CTO)"), ""))

    # known = 真正解析成功的检查项数。为 0 表示这项技能什么都没查到 ——
    # 此时 score 恒为初始的 100，那是「没扣分」而不是「很干净」，
    # 拿它参与合成会把综合分推高。见 composite()。
    known = len([g for g in sig if g[0] != "info"])
    return {"id": "ca_audit", "title": L("合约安全", "Contract"), "score": round(clamp(score)),
            "signals": sig, "unknown": unknown, "known": known}


# ── 技能 ② 持仓结构 ───────────────────────────────────────────────────────
def skill_holders(info, sec, L):
    stat = info.get("stat") or {}
    tags = info.get("wallet_tags_stat") or {}
    score = 100.0
    sig, unknown = [], []

    top10 = f(stat.get("top_10_holder_rate") or sec.get("top_10_holder_rate"))
    if has((stat, "top_10_holder_rate"), (sec, "top_10_holder_rate")):
        if top10 > 0.5:
            score -= 25
            sig.append(("bad", L("前十地址控盘 %s" % pct(top10), "Top 10 hold %s" % pct(top10)),
                        L("单点砸盘可直接归零", "one dump can zero it")))
        elif top10 > 0.30:
            score -= 14
            sig.append(("warn", L("前十地址持仓 %s 偏高" % pct(top10),
                                  "Top 10 hold %s — elevated" % pct(top10)), ""))
        else:
            sig.append(("good", L("筹码分散，前十仅 %s" % pct(top10),
                                  "Holdings dispersed — top 10 only %s" % pct(top10)), ""))
    else:
        unknown.append(L("前十集中度", "top-10 concentration"))

    dev_hold = max(f(stat.get("dev_team_hold_rate")), f(stat.get("creator_hold_rate")))
    dev_known = has((stat, "dev_team_hold_rate"), (stat, "creator_hold_rate"))
    if dev_known:
        if dev_hold > 0.05:
            score -= 20
            sig.append(("bad", L("Dev 仍持仓 %s" % pct(dev_hold, 2),
                                 "Dev still holds %s" % pct(dev_hold, 2)),
                        L("随时可砸", "can dump at any time")))
        elif dev_hold > 0.02:
            score -= 10
            sig.append(("warn", L("Dev 持仓 %s" % pct(dev_hold, 2),
                                  "Dev holds %s" % pct(dev_hold, 2)), ""))
        else:
            sig.append(("good", L("Dev 已清仓/无持仓", "Dev has exited / holds nothing"), ""))
    else:
        unknown.append(L("Dev 持仓", "dev holdings"))

    bundler = f(stat.get("top_bundler_trader_percentage"))
    if has((stat, "top_bundler_trader_percentage")):
        if bundler > 0.3:
            score -= 20
            sig.append(("bad", L("捆绑开盘占比 %s" % pct(bundler),
                                 "Bundled launch share %s" % pct(bundler)),
                        L("同一批钱包分仓砸盘", "one cohort splitting the dump")))
        elif bundler > 0.1:
            score -= 8
            sig.append(("warn", L("捆绑开盘占比 %s" % pct(bundler),
                                  "Bundled launch share %s" % pct(bundler)), ""))
    else:
        unknown.append(L("捆绑开盘占比", "bundled-launch share"))

    sniper = f(stat.get("top70_sniper_hold_rate"))
    if has((stat, "top70_sniper_hold_rate")):
        if sniper > 0.15:
            score -= 15
            sig.append(("bad", L("狙击盘仍持有 %s" % pct(sniper),
                                 "Snipers still hold %s" % pct(sniper)),
                        L("开盘抢跑的筹码还没出完", "front-run supply not yet distributed")))
        elif sniper > 0.05:
            score -= 6
            sig.append(("warn", L("狙击盘持有 %s" % pct(sniper),
                                  "Snipers hold %s" % pct(sniper)), ""))
        else:
            sig.append(("good", L("狙击盘已基本出清（%s）" % pct(sniper, 2),
                                  "Snipers largely cleared (%s)" % pct(sniper, 2)), ""))
    else:
        unknown.append(L("狙击盘持仓", "sniper holdings"))

    rat = f(stat.get("top_rat_trader_percentage"))
    if rat > 0.05:
        score -= 12
        sig.append(("bad", L("老鼠仓占比 %s" % pct(rat), "Insider-wallet share %s" % pct(rat)), ""))

    bot = f(stat.get("bot_degen_rate"))
    if bot > 0.5:
        score -= 10
        sig.append(("warn", L("机器人交易占比 %s" % pct(bot), "Bot trading share %s" % pct(bot)),
                    L("成交量含水", "volume is inflated")))

    smart = f(tags.get("smart_wallets"))
    if smart > 0:
        sig.append(("good", L("%d 个聪明钱地址在场" % int(smart),
                              "%d smart-money wallets present" % int(smart)),
                    L("统计上限 1000", "counter caps at 1000")))

    hc = f(stat.get("holder_count") or info.get("holder_count"))
    if hc and hc < 200:
        score -= 10
        sig.append(("warn", L("持有人只有 %d 个" % int(hc), "Only %d holders" % int(hc)),
                    L("盘子太小，一笔单就能拉爆", "tiny float")))

    known = len([g for g in sig if g[0] != "info"])
    return {"id": "holders", "title": L("持仓结构", "Holder structure"),
            "score": round(clamp(score)), "signals": sig, "unknown": unknown,
            "known": known}


# ── 技能 ③ K 线形态（与 gmgn-kline-pattern 同一套规则）───────────────────
def _ema(v, n):
    if not v:
        return []
    k = 2.0 / (n + 1)
    o = [v[0]]
    for x in v[1:]:
        o.append(x * k + o[-1] * (1 - k))
    return o


def _atr(rows, n=14):
    if len(rows) < 2:
        return 0.0
    t = [max(rows[i]["high"] - rows[i]["low"],
             abs(rows[i]["high"] - rows[i - 1]["close"]),
             abs(rows[i]["low"] - rows[i - 1]["close"])) for i in range(1, len(rows))][-n:]
    c = rows[-1]["close"] or 1
    return (sum(t) / len(t)) / c if t else 0.0


def _slope(c, n=20):
    s = c[-n:]
    if len(s) < 3:
        return 0.0
    m = len(s)
    xb = (m - 1) / 2.0
    yb = sum(s) / m
    num = sum((i - xb) * (v - yb) for i, v in enumerate(s))
    den = sum((i - xb) ** 2 for i in range(m)) or 1
    return (num / den) * m / (yb or 1)


def skill_kline(rows, L):
    if len(rows) < 8:
        return {"id": "kline", "title": L("K 线形态", "Price action"), "score": 50,
                "signals": [], "unknown": [L("K 线数据", "candles")], "known": 0}
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    last = rows[-1]
    e9, e21 = _ema(closes, 9), _ema(closes, 21)
    sl, atr = _slope(closes), _atr(rows)
    hi = max(r["high"] for r in rows)
    lo = min(r["low"] for r in rows)
    dd = (hi - last["close"]) / hi if hi else 0
    ufl = (last["close"] - lo) / lo if lo else 0
    prev = vols[-21:-1]
    sma = sum(prev) / len(prev) if prev else 0
    vr = vols[-1] / sma if sma else 1.0

    score = 50.0
    sig = []
    up = e9[-1] > e21[-1]
    if up:
        score += 12
        sig.append(("good", L("EMA9 在 EMA21 上方，短期多头结构",
                              "EMA9 above EMA21 — bullish structure"), ""))
    else:
        score -= 12
        sig.append(("bad", L("EMA9 跌破 EMA21，短期空头结构",
                             "EMA9 below EMA21 — bearish structure"), ""))
    p = sl * 100
    if sl > 0.15:
        score += 15
        sig.append(("good", L("近 20 根单边上行 +%.0f%%" % p,
                              "Last 20 bars trend up +%.0f%%" % p), ""))
    elif sl > 0.02:
        score += 6
        sig.append(("good", L("温和上行 +%.1f%%" % p, "Mild uptrend +%.1f%%" % p), ""))
    elif sl < -0.15:
        score -= 15
        sig.append(("bad", L("近 20 根单边下行 %.0f%%" % p,
                             "Last 20 bars trend down %.0f%%" % p), ""))
    elif sl < -0.02:
        score -= 6
        sig.append(("warn", L("缓慢阴跌 %.1f%%" % p, "Slow bleed %.1f%%" % p), ""))
    if vr > 3:
        u = last["close"] >= last["open"]
        score += 8 if u else -10
        sig.append(("good" if u else "bad",
                    L("最新一根放量 %.1fx" % vr, "Latest bar %.1fx volume" % vr), ""))
    elif vr < 0.3:
        score -= 5
        sig.append(("warn", L("成交量萎缩至均量 %s" % pct(vr, 0),
                              "Volume at %s of average" % pct(vr, 0)), ""))
    if dd > 0.6:
        score -= 15
        sig.append(("bad", L("较区间高点回撤 %s" % pct(dd, 0),
                             "Down %s from range high" % pct(dd, 0)), ""))
    elif dd > 0.3:
        score -= 6
        sig.append(("warn", L("较区间高点回撤 %s" % pct(dd, 0),
                              "Down %s from range high" % pct(dd, 0)), ""))
    elif dd < 0.05:
        score += 8
        sig.append(("good", L("贴着区间高点运行", "Trading at the range high"), ""))

    # ── 以下四条与 gmgn-kline-pattern 保持一致 ──
    # 早先这里少了它们，同一批 K 线两个包会差 10 分（量价背离是 -10）。
    # 三条 0 分的背景信号也补上：它们不影响分数，但影响用户看到的证据完整性。
    if abs(sl) <= 0.02:
        sig.append(("info", L("横盘震荡，方向未定", "Sideways — no direction yet"), ""))
    if atr > 0.15:
        sig.append(("warn", L("波动率极高 ATR %s，仓位要砍半" % pct(atr),
                              "Very high volatility, ATR %s — size down" % pct(atr)), ""))
    elif atr < 0.02:
        sig.append(("info", L("波动率低 ATR %s" % pct(atr),
                              "Low volatility, ATR %s" % pct(atr)), ""))
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
    if greens >= 5:
        sig.append(("warn", L("连续 %d 根阳线，短线超买，追高谨慎" % greens,
                              "%d green bars in a row — short-term overbought" % greens), ""))
    if reds >= 5:
        sig.append(("warn", L("连续 %d 根阴线，下跌趋势未止跌" % reds,
                              "%d red bars in a row — downtrend not exhausted" % reds), ""))
    if len(closes) > 40:
        p_now, p_prev = max(closes[-20:]), max(closes[-40:-20])
        v_now = sum(vols[-20:]) / 20
        v_prev = sum(vols[-40:-20]) / 20
        if p_now > p_prev * 1.02 and v_prev and v_now < v_prev * 0.7:
            score -= 10
            sig.append(("bad", L("量价背离：价格新高但成交量萎缩，上涨缺乏承接",
                                 "Divergence: new price high on shrinking volume — "
                                 "the move lacks participation"), ""))

    if sl > 0.25 and dd < 0.12:
        pat = L("单边拉升", "Vertical run-up")
    elif sl > 0.08 and dd < 0.25:
        pat = L("上升通道", "Uptrend channel")
    elif dd > 0.55 and sl < -0.1:
        pat = L("破位下跌", "Breakdown")
    elif dd > 0.35 and abs(sl) < 0.08:
        pat = L("高位派发/横盘", "Distribution at highs")
    elif sl < -0.2:
        pat = L("阴跌趋势", "Slow bleed")
    elif abs(sl) < 0.05 and atr < 0.05 and ufl < 0.2:
        pat = L("底部横盘", "Basing at lows")
    elif abs(sl) < 0.08 and atr > 0.08:
        pat = L("宽幅震荡", "Wide chop")
    else:
        pat = L("多头整理", "Bullish consolidation") if up else L("空头整理", "Bearish consolidation")

    return {"id": "kline", "title": L("K 线形态", "Price action"), "score": round(clamp(score)),
            "signals": sig, "unknown": [], "pattern": pat, "known": len(sig)}


# ── 合成 ──────────────────────────────────────────────────────────────────
def composite(skills, L):
    by = {s["id"]: s for s in skills if s}
    acc = tw = 0.0
    for sid, w in WEIGHTS.items():
        s = by.get(sid)
        # known == 0 的技能一个检查项都没解析成功，它的 100 分是「没扣分」而不是
        # 「很干净」。把它算进加权平均会凭空抬高综合分 —— 实测全空输入时会得到
        # 89 分，只靠蜜罐封顶才救回来；而封顶只在特定几项缺失时触发，兜不住。
        if not s or not s.get("known"):
            continue
        acc += s["score"] * w
        tw += w
    score = (acc / tw) if tw else 0.0
    if tw == 0:
        return {"score": 0, "action": L("没有任何一项检查取到数据，无法评分",
                                        "No check returned data — cannot score"),
                "bad": 0, "warn": 0,
                "unknown": [u for s in skills for u in (s.get("unknown") or [])],
                "capped": L("无数据", "no data")}

    unknown = []
    for s in skills:
        unknown += s.get("unknown") or []

    capped = None
    audit = by.get("ca_audit")
    if audit and audit["score"] <= 5:
        score = min(score, 8)
        capped = L("蜜罐一票否决", "honeypot veto")
    # 关键项未查到就不许打高分 —— 见模块开头
    key_missing = [u for u in unknown
                   if u in (L("蜜罐检测", "honeypot check"), L("是否开源", "open-source status"))]
    if key_missing and score > 59:
        score = 59
        capped = L("关键项未查到", "key checks unavailable")

    bad = sum(1 for s in skills for g in s["signals"] if g[0] == "bad")
    warn = sum(1 for s in skills for g in s["signals"] if g[0] == "warn")

    if capped == L("关键项未查到", "key checks unavailable"):
        act = L("关键项未查到（%s），不足以判断安全性" % "、".join(key_missing),
                "Key checks unavailable (%s) — not enough to judge safety"
                % ", ".join(key_missing))
    elif score >= 75:
        act = L("值得重点关注", "Worth a close look")
    elif score >= 60:
        act = L("可小仓位试单", "A small position is defensible")
    elif score >= 45:
        act = L("观察为主，等待更明确信号", "Watch only — wait for a clearer signal")
    elif score >= 30:
        act = L("风险偏高，非博弈型选手勿碰", "Risky — not for non-degens")
    else:
        act = L("建议规避", "Avoid")

    return {"score": round(score), "action": act, "bad": bad, "warn": warn,
            "unknown": unknown, "capped": capped}


# ── 输出 ──────────────────────────────────────────────────────────────────
MARK = {"good": "✅", "warn": "⚠️ ", "bad": "🔴", "info": "· "}


def _w(t):
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in t)


def pad(t, n):
    return t + " " * max(0, n - _w(t))


def bar(score, width=14):
    n = int(round(score / 100.0 * width))
    return "█" * n + "░" * (width - n)


def render(info, skills, comp, addr, chain, lang):
    zh = lang == "zh"

    def L(c, e):
        return c if zh else e

    price = info.get("price") or {}
    pool = info.get("pool") or {}
    out = []
    out.append("%s · %s" % (L("CA 综合尽调", "Contract due diligence"), chain.upper()))
    out.append("%s  %s" % (info.get("symbol") or "?", addr))
    out.append("─" * 66)
    out.append("%s %d / 100    %s" % (L("综合", "Composite"), comp["score"], comp["action"]))
    out.append("%s %d %s · %d %s%s" % (
        L("其中", "of which"), comp["bad"], L("条红色警报", "critical"),
        comp["warn"], L("条提示", "warnings"),
        L("　（封顶：%s）" % comp["capped"], "  (capped: %s)" % comp["capped"])
        if comp["capped"] else ""))
    out.append("")
    for s in skills:
        if not s.get("known"):
            # 没查到任何东西的技能不能显示 100 —— 那会让人以为它通过了检查
            out.append("  %s %s  %s" % (pad(s["title"], 17), "·" * 14,
                                        L("无数据", "no data")))
            continue
        out.append("  %s %s %3d" % (pad(s["title"], 17), bar(s["score"]), s["score"]))
        if s.get("pattern"):
            out.append("  %s %s" % (pad("", 17), s["pattern"]))
    out.append("")
    out.append(L("盘面", "Market"))
    mc = f(price.get("price")) * f(info.get("total_supply"))
    out.append("  %s %s   %s %s   %s %s" % (
        L("市值", "Mcap"), usd(mc),
        L("池子", "Pool"), usd(pool.get("liquidity") or info.get("liquidity")),
        L("持有人", "Holders"), "{:,}".format(int(f(info.get("holder_count"))))))
    out.append("  %s %s   %s %s" % (
        L("1h 成交", "1h volume"), usd(price.get("volume_1h")),
        L("1h 买/卖", "1h buys/sells"),
        "%d / %d" % (f(price.get("buys_1h")), f(price.get("sells_1h")))))
    out.append("")
    out.append(L("逐项依据", "Per-item evidence"))
    for s in skills:
        if not s["signals"]:
            continue
        out.append("  [%s]" % s["title"])
        for level, text, detail in s["signals"]:
            line = "    %s %s" % (MARK[level], text)
            if detail:
                line += L("　—— %s" % detail, "  — %s" % detail)
            out.append(line)
    if comp["unknown"]:
        out.append("")
        out.append("%s %s" % (L("未查到的项", "Not available"), "、".join(comp["unknown"])
                              if zh else ", ".join(comp["unknown"])))
        out.append(L("  缺失的项不计分，也不当作好消息 —— 上面的分数只由查到的证据构成。",
                     "  Missing items are not scored and never counted as good news — "
                     "the score above rests only on evidence actually obtained."))
    out.append("")
    out.append("─" * 66)
    out.append(L("规则引擎输出，仅做信息聚合，不构成投资建议。"
                 "数据源：GMGN 官方 OpenAPI（token/info · token/security · market/token_kline）。",
                 "Rule-engine output — information aggregation only, not investment advice. "
                 "Source: GMGN official OpenAPI (token/info · token/security · "
                 "market/token_kline)."))
    return "\n".join(out)


# ── 主流程 ────────────────────────────────────────────────────────────────
def check(addr, chain):
    c = (chain or "").strip().lower()
    if not c.replace("-", "").isalnum():
        die("链名不合法：%r" % chain)
    a = (addr or "").strip()
    if c in NON_EVM:
        ok = 32 <= len(a) <= 44 and all(
            ch in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for ch in a)
        if not ok:
            die("地址不像 %s 链的 base58 地址" % c)
    else:
        if not (a.startswith("0x") and len(a) == 42
                and all(ch in "0123456789abcdefABCDEF" for ch in a[2:])):
            die("地址不像 EVM 地址（0x + 40 位十六进制）")
    return a, c


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(__doc__ or "")
        sys.exit(2)
    addr, chain = check(sys.argv[1], sys.argv[2])
    lang = sys.argv[3] if len(sys.argv) > 3 else "zh"
    if lang not in ("zh", "en"):
        lang = "zh"
    zh = lang == "zh"

    def L(c, e):
        return c if zh else e

    info = run_cli(["token", "info", "--chain", chain, "--address", addr]) or {}
    if not info:
        die("这个地址在 %s 链上查不到。确认链选对了、合约地址没写错。" % chain)
    sec = run_cli(["token", "security", "--chain", chain, "--address", addr],
                  optional=True) or {}
    kl = run_cli(["market", "kline", "--chain", chain, "--address", addr,
                  "--resolution", "15m"], optional=True) or {}

    raw = kl if isinstance(kl, list) else (kl.get("list") or [])
    rows = []
    for k in raw:
        try:
            t = float(k.get("time") or 0)
            rows.append({"t": int(t / 1000 if t > 1e12 else t),
                         "open": float(k.get("open") or 0), "high": float(k.get("high") or 0),
                         "low": float(k.get("low") or 0), "close": float(k.get("close") or 0),
                         "volume": float(k.get("volume") or 0)})
        except (TypeError, ValueError):
            continue
    rows = [r for r in rows if r["close"] > 0]

    skills = [skill_ca(info, sec, L), skill_holders(info, sec, L), skill_kline(rows, L)]
    comp = composite(skills, L)
    print(render(info, skills, comp, addr, chain, lang))


if __name__ == "__main__":
    main()
