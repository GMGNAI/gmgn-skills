#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""X 叙事 & 讨论度 —— 一个代币在 X 上到底有没有人聊。

前置条件:
    npm install -g gmgn-cli   （一次即可；随后 gmgn-cli config 配好 API Key）

用法:
    python3 narrative.py <address> <chain> [lang] [--kol N]

GMGN 侧的数据一律经由 gmgn-cli 取（本仓库 CLAUDE.md 的第一条硬性规则），所以这个
包**完全不接触 API Key，也不接触私钥**。只用四条 read-only 命令：
`token info` / `token holders` / `track kol` / `track smartmoney`。

X 与搜索引擎不是 GMGN 域名，走各自的公开接口（X 的 syndication 嵌入接口，无需登录）。
零依赖，Python 3.9+ 标准库。

══ 这个技能最容易被误读的一条 ══
X 对爬虫基本封闭。搜索引擎返回 0 结果**推不出「没人聊」** —— 只能说明搜不到。
所以本项**只按抓到的证据加分，不因搜不到而扣分**。看到低分请先看「覆盖度」
那一行：它告诉你这个分数是建立在多少条时间线之上的。

四路信息合流，任何一路失败都降级而不是报错：
    ① 项目方 X 账号时间线
    ② 持有人绑定的 X 账号（token_top_holders 每行自带 twitter_username，
       白捡的、且与本币直接相关 —— 优先级高于全局 KOL 池）
    ③ 全局 KOL / 聪明钱池（从官方 /v1/user/kol 与 /v1/user/smartmoney 建）
    ④ 公开搜索引擎

两条硬规则：
    · 只有 24 小时窗口内的提及参与计分，更早的归到「历史提及」单独展示
    · 每条提及都必须有硬凭据（CA / $符号 / 名称+链上语境词），
      上游自己的喊单与广场提及计数一律不采信 —— 那是二手结论
"""
from __future__ import annotations

import sys
import time

import openapi as API
from i18n import T, set_lang, check_no_cjk, missing
import web2
import xsearch
import xsocial as X

def f(x, default=0.0):
    """把上游返回的字符串数字安全转 float。"""
    if x is None or x == "":
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def pct(x, digits=2):
    return "%.*f%%" % (digits, f(x) * 100)


def usd(x):
    v = f(x)
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a >= 1e9:
        return "%s$%.2fB" % (sign, a / 1e9)
    if a >= 1e6:
        return "%s$%.2fM" % (sign, a / 1e6)
    if a >= 1e3:
        return "%s$%.2fK" % (sign, a / 1e3)
    if a >= 1:
        return "%s$%.2f" % (sign, a)
    if a == 0:
        return "$0"
    return "%s$%.6g" % (sign, a)


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def _sig(level, text, detail=None):
    return {"level": level, "text": text, "detail": detail}


def _metric(label, value, tone="neutral", hint=None):
    return {"label": label, "value": value, "tone": tone, "hint": hint}


def grade(score):
    if score >= 80:
        return "优秀"
    if score >= 65:
        return "良好"
    if score >= 50:
        return "中性"
    if score >= 35:
        return "偏弱"
    return "高危"


def x_narrative(project, scan, search_res=None, web2_res=None, symbol=None, name=None,
                source_tweet=None):
    """X 叙事 & 讨论度。

    四路信息合流，任何一路失败都降级而不是报错：
      · source_tweet  行情源的 twitter 字段常直接指向"首发叙事推文"
      · project       项目方账号时间线
      · scan          打狗 KOL 池 + 自动发现名单里的提及
      · search_res    公开搜索引擎搜 CA/$符号 拿到的全网讨论
      · web2_res      推文外链里的 Web2 叙事源（小红书/微博/抖音/新闻…）

    两条硬规则：
      1. **只有 24 小时窗口内的提及参与计分**，更早的归到「历史提及」单独展示；
      2. 每条提及都必须有硬凭据（CA / $符号 / 名称+链上语境词），
         上游自己的喊单与广场提及计数一律不采信 —— 那是二手结论。
    """
    signals, metrics = [], []
    score = 35.0
    now = time.time()

    scan = scan or {}
    search_res = search_res or {}
    web2_res = web2_res or {}
    raw_mentions = scan.get("hits") or []              # 已按 24h 窗口过滤
    covered, total_kol = scan.get("covered", 0), scan.get("total", 0)
    raw_web = search_res.get("tweets") or []           # 同样只含窗口内
    historical = (scan.get("historical") or []) + (search_res.get("historical") or [])
    window_h = int((scan.get("window") or 86400) / 3600)

    # 计分口径区分「主动搜到的」和「扫时间线撞上的」：
    #   · 搜索结果里的 name 档是我们**拿这个币名去搜**才回来的 → 算数
    #   · 时间线扫描里的 context 档是**撞上的** → 只当疑似，不计分
    # 「utility + pancake」那类噪声出在后者，所以只掐后者。
    HARD = ("ca", "cashtag")
    hard = [m for m in (raw_mentions + raw_web) if m.get("match") in HARD]
    soft = [m for m in raw_mentions if m.get("match") == "context"]
    mentions = [m for m in raw_mentions if m.get("match") in HARD]
    web_tweets = [m for m in raw_web if m.get("match") in HARD + ("name",)]
    by_name = [m for m in raw_web if m.get("match") == "name"]

    # 打狗 KOL（链上验证过盈利的）vs 其它提及
    kol_hits = [m for m in mentions if m.get("kol")]
    other_hits = [m for m in mentions if not m.get("kol")]
    web_kol_hits = [t for t in web_tweets if t.get("kol")]

    texts = []
    if source_tweet:
        texts.append(source_tweet.get("text") or "")
    if project:
        texts += [t["text"] for t in (project.get("latest") or [])]
    texts += [m["text"] for m in mentions[:40]]
    texts += [t["text"] for t in web_tweets[:20]]
    for x in (name, symbol):
        if x:
            texts.append(x)

    # ---- 叙事源推 ----
    if source_tweet:
        eng = (source_tweet.get("likes", 0) + source_tweet.get("retweets", 0) * 2
               + source_tweet.get("replies", 0))
        signals.append(_sig("info", T("叙事源推：@%s") % (source_tweet.get("handle") or "?"),
                            (source_tweet.get("text") or "")[:120]))
        if eng > 500:
            score += 12
            signals.append(_sig("good", T("源推互动 %s") % "{:,}".format(eng)))
        elif eng < 30:
            score -= 6
            signals.append(_sig("warn", T("源推互动仅 %d") % eng, T("叙事没起来")))

    # ---- 项目方 ----
    if project:
        fol = project.get("followers") or 0
        metrics.append(_metric(T("项目方粉丝"), "{:,}".format(fol),
                               "good" if fol > 20000 else "warn" if fol < 1000 else "neutral"))
        metrics.append(_metric(T("近 7 天发推"), str(project.get("posts_7d") or 0),
                               "good" if (project.get("posts_7d") or 0) >= 3 else "warn"))
        if fol > 100000:
            score += 22
            signals.append(_sig("good", T("项目方 %s 粉丝，量级罕见") % "{:,}".format(fol)))
        elif fol > 10000:
            score += 13
            signals.append(_sig("good", T("项目方 %s 粉丝") % "{:,}".format(fol)))
        elif fol < 500:
            score -= 8
            signals.append(_sig("warn", T("项目方仅 %d 粉丝") % fol, T("冷启动阶段")))
        if project.get("partial"):
            signals.append(_sig("info", T("项目方时间线不可读，仅拿到单条源推"),
                                T("该账号可能未开放嵌入，或正处于 X 限流冷却")))
        elif (project.get("posts_7d") or 0) == 0:
            score -= 10
            signals.append(_sig("bad", T("项目方 7 天没发推"), T("运营停摆")))
        elif (project.get("posts_7d") or 0) >= 10:
            score += 7
            signals.append(_sig("good", T("项目方 7 天发了 %d 条，运营活跃")
                                % project["posts_7d"]))
    else:
        score -= 6
        signals.append(_sig("warn", T("没抓到项目方 X 账号"),
                            T("行情源的 twitter 字段可能指向一条推文而非账号主页")))

    # ---- 打狗 KOL（权重最高：链上实盘验证过的人在聊）----
    kol_all = {}
    for m in kol_hits + web_kol_hits:
        h = m.get("handle")
        if not h:
            continue
        e = kol_all.setdefault(h, {"handle": h, "author": m.get("author"),
                                   "avatar": m.get("avatar"), "count": 0,
                                   "engagement": 0, "hard": False, "evidence": None,
                                   "age_sec": None, "followers": m.get("followers", 0),
                                   "profit": (m.get("kol") or {}).get("profit", 0),
                                   "tags": (m.get("kol") or {}).get("tags", [])})
        e["count"] += 1
        e["engagement"] += m["likes"] + m["retweets"] * 2 + m["replies"]
        if m.get("match") in ("ca", "cashtag"):
            e["hard"] = True
        e["evidence"] = m.get("evidence") or e.get("evidence")
        e["age_sec"] = min(e.get("age_sec") or 1e12, m.get("age_sec") or 1e12)
    kol_list = sorted(kol_all.values(), key=lambda k: -k["profit"])
    kol_profit_sum = sum(k["profit"] for k in kol_list)

    metrics.insert(0, _metric(T("热点提及 %dh") % window_h,
                              T("%d 条") % len(set(m["id"] for m in (mentions + web_tweets))),
                              "good" if hard else "warn" if soft else "bad"))
    metrics.append(_metric(T("硬凭据 / 名称命中"), "%d / %d" % (len(hard), len(by_name)),
                           "good" if len(hard) >= 2 else "neutral",
                           T("名称命中来自主动搜索，计分；时间线撞词不计分")))
    metrics.append(_metric(T("打狗 KOL 提及"), str(len(kol_list)),
                           "good" if kol_list else "warn"))
    if kol_profit_sum:
        metrics.append(_metric(T("这些 KOL 累计盈利"), usd(kol_profit_sum), "good"))

    kol_hard = [k for k in kol_list if k.get("hard")]
    if len(kol_list) >= 5:
        score += 30
        signals.append(_sig("good", T("%d 个链上验证的打狗 KOL 在聊") % len(kol_list),
                            T("他们累计已实现盈利 %s —— 这批人下场通常意味着有共识")
                            % usd(kol_profit_sum)))
    elif len(kol_list) >= 2:
        score += 20
        signals.append(_sig("good", T("%d 个打狗 KOL 提及（%s）")
                            % (len(kol_list),
                               "、".join("@" + k["handle"] for k in kol_list[:3])),
                            T("累计已实现盈利 %s") % usd(kol_profit_sum)))
    elif len(kol_list) == 1:
        k = kol_list[0]
        score += 10
        signals.append(_sig("good", T("打狗 KOL @%s 提到了") % k["handle"],
                            T("该地址已实现盈利 %s；单点热度容易熄火") % usd(k["profit"])))
    else:
        score -= 8
        signals.append(_sig("warn", T("打狗 KOL 池里无人提及"),
                            T("已覆盖 %d/%d 个账号的时间线") % (covered, total_kol)))

    # ---- 全网讨论 ----
    state = search_res.get("state")
    web_eng = sum(t["likes"] + t["retweets"] * 2 + t["replies"] for t in web_tweets)
    if web_tweets:
        metrics.append(_metric(T("全网搜到讨论"), str(len(web_tweets)), "good"))
        metrics.append(_metric(T("讨论总互动"), "{:,}".format(web_eng), "neutral"))
        if len(web_tweets) >= 8:
            score += 16
            signals.append(_sig("good", T("全网搜到 %d 条讨论，合计互动 %s")
                                % (len(web_tweets), "{:,}".format(web_eng)),
                                T("叙事已经扩散到 KOL 池之外")))
        else:
            score += 8
            signals.append(_sig("good", T("全网搜到 %d 条讨论") % len(web_tweets)))
        distinct = len({t.get("handle") for t in web_tweets if t.get("handle")})
        if distinct >= 6:
            score += 6
            signals.append(_sig("good", T("%d 个不同账号在讨论") % distinct, T("不是单点刷屏")))
        elif distinct == 1 and len(web_tweets) > 2:
            score -= 5
            signals.append(_sig("warn", T("全部来自同一个账号"), T("疑似自导自演")))
        if search_res.get("rejected"):
            signals.append(_sig("info", T("搜索结果里剔掉了 %d 条不相关的")
                                % search_res["rejected"],
                                T("水化后用同一套强框定规则做了二次校验")))
    elif state in ("queued", "cooling"):
        signals.append(_sig("info", T("全网搜索%s")
                            % (T("排队中") if state == "queued" else T("限流冷却中")),
                            T("搜索引擎对脚本流量敏感，结果会在下次查询同一个 CA 时补上")))
    else:
        # 这里必须说清楚：X 的内容早就基本不在公开搜索索引里了（X 封爬虫），
        # 搜索引擎 0 命中**不能推断成没人聊**。实测同一个 CA 在 X 站内搜索
        # 有大量讨论，但 Bing / Brave / DDG / Yandex / Mojeek 全部 0 条。
        # 之前写「要么太新，要么确实没人聊」是误导，已改。
        signals.append(_sig("info", T("搜索引擎没有这个 CA 的收录"),
                            T("X 对爬虫基本封闭，搜索引擎的 0 结果**推不出「没人聊」**"
                              "——要判断真实声量请直接在 X 站内搜索。"
                              "本项只按已抓到的证据打分，不因搜不到而扣分")))

    # ---- 其它提及 / 时效 ----
    if other_hits:
        metrics.append(_metric(T("名单内其它提及"), str(len(other_hits)), "neutral"))

    all_hits = mentions + web_tweets
    fresh = [m for m in all_hits if m.get("heat") == "hot"]
    if fresh:
        score += 12
        signals.append(_sig("good", T("近 6 小时有 %d 条新提及") % len(fresh), T("热度在升温")))
    elif all_hits:
        newest = max((m.get("ts") or 0) for m in all_hits)
        if newest:
            signals.append(_sig("info", T("最新一条提及在 %.1f 小时前")
                                % ((now - newest) / 3600)))
    # 叙事高峰经常落在窗口外（比如「牛来」那部电影是 47 小时前爆的）。
    # 计分照规矩只认窗口内，但必须把高峰点出来 —— 否则「热度已过」会误导成「从没热过」。
    peak = max(historical, key=lambda m: m.get("engagement",
                                               m["likes"] + m["retweets"] * 2), default=None)
    peak_eng = (peak.get("engagement") or (peak["likes"] + peak["retweets"] * 2)) \
        if peak else 0
    if peak and peak_eng >= 200:
        hrs = (now - (peak.get("ts") or now)) / 3600
        metrics.append(_metric(T("叙事高峰"), T("%s 互动 · %.0fh前") % ("{:,}".format(peak_eng), hrs),
                               "warn" if hrs > window_h else "good"))
        signals.append(_sig("info" if all_hits else "warn",
                            T("叙事高峰在 %.0f 小时前（单条互动 %s，@%s）")
                            % (hrs, "{:,}".format(peak_eng), peak.get("handle") or "?"),
                            (peak.get("text") or "")[:100]))

    if not all_hits and historical:
        score -= 12
        newest_old = max((m.get("ts") or 0) for m in historical)
        signals.append(_sig("bad", T("%d 小时内零提及") % window_h,
                            T("有 %d 条历史讨论，最近一条在 %.1f 小时前 —— 按规矩不计分")
                            % (len(historical),
                               (now - newest_old) / 3600 if newest_old else 0)))
    elif historical:
        signals.append(_sig("info", T("另有 %d 条历史提及（超出 %dh 窗口）") % (len(historical),
                                                                            window_h),
                            T("已归档，不参与打分")))

    if soft:
        signals.append(_sig("info", T("另有 %d 条疑似相关（只匹配到名称+语境词）") % len(soft),
                            T("没贴 CA 也没带 $符号，可能只是同名词撞车 —— 已排除在计分外")))

    # ---- Web2 叙事源 ----
    w2_items = web2_res.get("items") or []
    if w2_items:
        plats = "、".join("%s×%d" % (p["platform"], p["count"])
                         for p in (web2_res.get("summary") or [])[:3])
        score += min(14, 6 + len(w2_items) * 2)
        top = w2_items[0]
        signals.append(_sig("good", T("有 Web2 叙事背书：%s") % plats,
                            (top.get("title") or top.get("final_url") or top["url"])[:110]))
        metrics.append(_metric(T("Web2 叙事源"), str(web2_res.get("total") or len(w2_items)),
                               "good"))
    else:
        signals.append(_sig("info", T("没找到 Web2 叙事源"),
                            T("推文外链里没有小红书/微博/抖音/新闻这类站外内容")))

    narratives = []
    try:
        from xsocial import classify_narrative
        narratives = classify_narrative(texts)
    except Exception:
        narratives = []
    if narratives:
        signals.append(_sig("info", T("叙事归类：%s")
                            % " / ".join(n["label"] for n in narratives),
                            T("命中关键词：%s") % ", ".join(narratives[0]["keywords"])))

    if total_kol and covered < total_kol:
        signals.append(_sig("info", T("KOL 池覆盖 %d/%d") % (covered, total_kol),
                            T("其余账号后台仍在预热，X 公开接口有 IP 限流")))

    score = clamp(score)
    if not all_hits and historical:
        verdict = (T("叙事高峰已过（%.0fh 前互动 %s），%dh 窗口内无人再提")
                   % ((now - (peak.get("ts") or now)) / 3600,
                      "{:,}".format(peak_eng), window_h)) if peak_eng >= 200 \
            else T("%dh 内无人提及，热度已过") % window_h
    elif len(kol_hard) >= 3 and (fresh or w2_items):
        verdict = T("打狗 KOL 已下场，叙事在扩散")
    elif len(kol_list) >= 1 and w2_items:
        verdict = T("有 Web2 叙事 + KOL 关注")
    elif w2_items:
        verdict = T("有 Web2 叙事，但链上圈子还没跟")
    elif web_tweets or mentions:
        verdict = T("有讨论但尚未破圈")
    elif project and (project.get("followers") or 0) > 10000:
        verdict = T("项目方有基本盘，但 KOL 尚未跟进")
    else:
        verdict = T("社媒声量微弱")

    return {"id": "x_narrative", "title": T("X 叙事 & 讨论度"), "score": round(score),
            "verdict": verdict, "signals": signals, "metrics": metrics,
            "data": {"project": project, "source_tweet": source_tweet,
                     "kol_mentions": (kol_hits + web_kol_hits)[:10],
                     "other_mentions": other_hits[:6],
                     "historical": historical[:8],
                     "suspect": soft[:6],
                     "window_hours": window_h,
                     "evidence": {"hard": len(hard), "soft": len(soft)},
                     "search": {"tweets": web_tweets[:10], "state": state,
                                "engine": search_res.get("engine"),
                                "age": search_res.get("age"),
                                "rejected": search_res.get("rejected", 0),
                                "found": search_res.get("found_ids", 0)},
                     "web2": web2_res,
                     "kols": kol_list[:12], "narratives": narratives,
                     "coverage": {"covered": covered, "total": total_kol,
                                  "pool_size": scan.get("pool_size", 0)},
                     "total_engagement": web_eng}}

# ══════════════════════════════════════════════════════════════════════════
# 编排 —— 把四路数据凑齐再交给 x_narrative()
# ══════════════════════════════════════════════════════════════════════════
NON_EVM = {"sol", "solana", "tron", "trx", "sui", "ton", "apt", "aptos"}


def die(msg):
    sys.stderr.write("错误：%s\n" % msg)
    sys.exit(2)


def check(addr, chain):
    c = (chain or "").strip().lower()
    if not c.replace("-", "").isalnum():
        die("链名不合法：%r" % chain)
    a = (addr or "").strip()
    if c in NON_EVM:
        ok = 32 <= len(a) <= 44 and all(
            ch in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
            for ch in a)
        if not ok:
            die("地址不像 %s 链的 base58 地址" % c)
    else:
        if not (a.startswith("0x") and len(a) == 42
                and all(ch in "0123456789abcdefABCDEF" for ch in a[2:])):
            die("地址不像 EVM 地址（0x + 40 位十六进制）")
    return a, c


def warm(handles, budget_s, log):
    """在时间预算内尽量多抓时间线，抓不完就如实报覆盖度。

    这一步是整个技能里最慢的：一条时间线约 1 秒。串行抓 200 个账号要三分多钟，
    没有哪个调用方愿意等。所以给一个**时间预算**，到点就停，然后把
    「覆盖 N/M」写进结论 —— 覆盖度低会让分数偏低，那是诚实的低，
    不是「没人聊」。
    """
    got, t0, per = [], time.time(), 2.5   # per = 单条时间线的实测耗时上界
    for h in handles:
        # 预算要为「这一次抓取本身」留出时间，否则最后一次必然超支。
        # 实测单条约 2.5s（X 对连续请求有 IP 限流，比单发的 1.1s 慢一倍多）。
        if time.time() - t0 + per > budget_s:
            break
        try:
            X.refresh_timeline(h, wait=True)
        except Exception:
            pass
        tl = X.timeline(h, allow_network=False)
        if tl:
            got.append(h)
    log("  时间线覆盖 %d/%d（预算 %ds，用时 %.1fs）"
        % (len(got), len(handles), budget_s, time.time() - t0))
    return got


def run(addr, chain, lang, kol_n, budget_s, quiet):
    def log(m):
        if not quiet:
            sys.stderr.write(m + "\n")

    info = API.token_info(addr, chain)
    if not info:
        die("这个地址在 %s 链上查不到。确认链选对了、合约地址没写错。" % chain)
    symbol = info.get("symbol") or ""
    name = info.get("name") or ""
    link = info.get("link") or {}
    log("① %s（%s）" % (symbol, name))

    # ── 项目方账号 ──
    proj_handle = X.resolve_handle(link.get("twitter_username") or "")
    project, project_tl = {}, []
    if proj_handle:
        try:
            X.refresh_timeline(proj_handle, wait=True)
        except Exception:
            pass
        project_tl = X.timeline(proj_handle, allow_network=False) or []
        project = X.profile(proj_handle, allow_network=False) or {}
        log("② 项目方 @%s：%d 条推文" % (proj_handle, len(project_tl)))
    else:
        log("② 没抓到项目方 X 账号（行情源的 twitter 字段可能指向一条推文而非账号主页）")

    # ── 持有人绑定的 X 账号（与本币直接相关，优先级最高）──
    holders = API.token_top_holders(addr, chain)
    hh = X.handles_from_holders(holders)
    picked = [e["handle"] for e in hh[:kol_n]]
    log("③ %d 个持有人绑定了 X，按持仓取前 %d 个" % (len(hh), len(picked)))
    if picked:
        warm(picked, budget_s * 0.6, log)
    holder_tls = [X.timeline(h, allow_network=False) or [] for h in picked]

    # ── 全局 KOL / 聪明钱池（补充）──
    try:
        X.refresh_kol_pool()
    except Exception as e:
        log("   KOL 池刷新失败：%s" % str(e)[:60])
    pool = [k["handle"] for k in X.kol_pool() if k["handle"] not in picked][:kol_n]
    if pool:
        log("④ 全局池 %d 个账号" % len(pool))
        warm(pool, budget_s * 0.4, log)

    # 必须把实际预热过的名单传进去。不传的话 scan_mentions 会按**全池**统计，
    # 报出「覆盖 3/47」这种数字 —— 分母是没打算抓的账号，读起来像抓失败了 44 个。
    scan = X.scan_mentions(addr, symbol, name, handles=(picked + pool),
                           extra_timelines=[project_tl] + holder_tls)
    log("   %dh 窗口内提及 %d 条（另有 %d 条超窗归档），已覆盖 %d/%d 条时间线"
        % (int(scan["window"] / 3600), len(scan["hits"]),
           len(scan.get("historical") or []), scan["covered"], scan["total"]))

    # ── 搜索引擎 ──
    try:
        search_res = xsearch.search(addr, symbol) or {}
    except Exception as e:
        log("   搜索失败：%s" % str(e)[:60])
        search_res = {}
    log("⑤ 搜索引擎：%s，%d 条"
        % (search_res.get("engine") or "-", len(search_res.get("tweets") or [])))

    # ── Web2 外链 ──
    pool_tweets = (project_tl[:20] + scan["hits"]
                   + (search_res.get("tweets") or [])
                   + (search_res.get("historical") or []))
    try:
        w2 = web2.collect(pool_tweets)
    except Exception:
        w2 = {}
    log("⑥ Web2 叙事源 %d 个" % (w2.get("total") or 0))

    return (x_narrative(project, scan, search_res, w2, symbol, name),
            scan, search_res, symbol)


# ══════════════════════════════════════════════════════════════════════════
# 渲染
# ══════════════════════════════════════════════════════════════════════════
MARK = {"good": "✅", "warn": "⚠️ ", "bad": "🔴", "info": "· "}


def _w(t):
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in t)


def pad(t, n):
    return t + " " * max(0, n - _w(t))


def render(res, scan, addr, symbol, lang):
    zh = lang == "zh"

    def L(c, e):
        return c if zh else e

    out = []
    out.append("%s · %s" % (L("X 叙事 & 讨论度", "X narrative & chatter"), symbol or "?"))
    out.append(addr)
    out.append("─" * 66)
    out.append("%s %d / 100    %s" % (L("热度分", "Narrative score"),
                                      res["score"], res["verdict"]))
    out.append("")
    for m in res.get("metrics") or []:
        out.append("  %s %s" % (pad(m["label"], 26 if not zh else 18), m["value"]))
    out.append("")
    out.append("%s %d/%d" % (L("时间线覆盖", "Timelines covered"),
                             scan.get("covered", 0), scan.get("total", 0)))
    out.append(L("  覆盖度低会让分数偏低 —— 那是「没抓到」，不是「没人聊」。",
                 "  Low coverage lowers the score — that means 'not observed', "
                 "not 'nobody is talking'."))
    out.append("")
    out.append(L("逐项依据", "Per-item evidence"))
    for s in res.get("signals") or []:
        line = "  %s %s" % (MARK.get(s["level"], "· "), s["text"])
        if s.get("detail"):
            line += L("　—— %s" % s["detail"], "  — %s" % s["detail"])
        out.append(line)
    out.append("")
    out.append("─" * 66)
    out.append(L("X 对爬虫基本封闭，搜索引擎的 0 结果**推不出「没人聊」**。"
                 "本项只按抓到的证据打分，不因搜不到而扣分。\n"
                 "规则引擎输出，仅做信息聚合，不构成投资建议。",
                 "X is effectively closed to crawlers, so zero search results **do not "
                 "mean nobody is talking**. This skill scores only the evidence it did "
                 "find and never deducts for a miss.\n"
                 "Rule-engine output — information aggregation only, not investment "
                 "advice."))
    return "\n".join(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 2:
        sys.stderr.write(__doc__ or "")
        sys.exit(2)
    addr, chain = check(args[0], args[1])
    lang = args[2] if len(args) > 2 else "zh"
    if lang not in ("zh", "en"):
        lang = "zh"
    set_lang(lang)
    kol_n, budget = 24, 45
    for fl in flags:
        if fl.startswith("--kol="):
            kol_n = max(1, min(200, int(fl.split("=", 1)[1] or 24)))
        if fl.startswith("--budget="):
            budget = max(5, min(600, int(fl.split("=", 1)[1] or 45)))
    quiet = "--quiet" in flags

    if not API.available():
        die("gmgn-cli not found. Install it once with:  npm install -g gmgn-cli\n"
            "       Then configure your API key with:   gmgn-cli config")

    try:
        res, scan, _, symbol = run(addr, chain, lang, kol_n, budget, quiet)
    except API.ApiError as e:
        die(str(e))
    text = render(res, scan, addr, symbol, lang)
    # 英文模式下不该有中文残留。漏翻要响亮地失败 —— 静默输出中文比报错糟得多，
    # 因为调用方（AI agent）会把它原样贴给英文用户。
    bad = check_no_cjk(text, allow=(symbol, addr))
    if bad:
        sys.stderr.write("警告：英文输出里有 %d 行中文残留，对照表不全：\n" % len(bad))
        for ln in bad[:6]:
            sys.stderr.write("   %s\n" % ln.strip()[:90])
        if missing():
            sys.stderr.write("   缺翻译的串：%s\n" % "; ".join(missing())[:300])
    print(text)


if __name__ == "__main__":
    main()
