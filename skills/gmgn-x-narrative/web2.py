# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""Web2 叙事源。

BSC 上的中文 meme 很多不是"链上原生叙事"，而是**先在 Web2 火起来**，
再被人搬到链上发币 —— 比如小红书某条爆款笔记、微博热搜、抖音视频、一条新闻。

这类叙事的痕迹就藏在推文的外链里（`entities.urls[].expanded_url`）。
本模块干三件事：
  1. 从项目方推文 / 源推 / KOL 提及里把非 X 外链抽出来；
  2. 按域名归类平台（小红书 / 微博 / 抖音 / B站 / 新闻 …），
     并剔除行情工具类链接（dexscreener、行情站、四meme 之类，那不是叙事）；
  3. 跟随短链跳转拿最终 URL 和页面标题，让"到底在讲什么"能直接读出来。

标题抓取是尽力而为：很多中文平台对脚本返回风控页，拿不到标题就只展示平台和链接，
不影响判断"这个盘有 Web2 叙事背书"这个结论本身。
"""
from __future__ import annotations

import gzip
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

import safefetch as NG

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 平台归类：(展示名, 图标, 域名关键词, 是否算 Web2 叙事源)
PLATFORMS = [
    ("小红书", "📕", ["xiaohongshu.com", "xhslink.c", "xhslink.com"], True),
    ("微博", "🅦", ["weibo.com", "weibo.cn", "t.cn"], True),
    ("抖音", "🎵", ["douyin.com", "iesdouyin.com", "v.douyin"], True),
    ("快手", "⚡", ["kuaishou.com", "gifshow.com"], True),
    ("哔哩哔哩", "📺", ["bilibili.com", "b23.tv"], True),
    ("知乎", "🅩", ["zhihu.com", "zhihu.cn"], True),
    ("微信公众号", "💬", ["mp.weixin.qq.com"], True),
    ("YouTube", "▶", ["youtube.com", "youtu.be"], True),
    ("TikTok", "🎶", ["tiktok.com"], True),
    ("Instagram", "📷", ["instagram.com"], True),
    ("Reddit", "🅡", ["reddit.com", "redd.it"], True),
    ("Telegram", "✈", ["t.me", "telegram.me"], False),
    ("新闻媒体", "📰", ["news.", "sina.com", "163.com", "qq.com/news", "sohu.com",
                        "thepaper.cn", "reuters.com", "bloomberg.com", "cnbc.com",
                        "coindesk.com", "cointelegraph.com", "36kr.com", "ifeng.com",
                        "bbc.co", "nytimes.com", "wsj.com", "theblock.co"], True),
    ("长文 / 博客", "📝", ["medium.com", "mirror.xyz", "substack.com", "notion.site"], True),
    ("GitHub", "⌨", ["github.com"], False),
]

# 这些是行情/工具/交易链接，不是叙事
IGNORE = [
    "dexscreener.com", "gmgn.ai", "dextools.io", "birdeye.so", "pump.fun",
    "four.meme", "flap.sh", "pancakeswap", "uniswap", "bscscan.com", "etherscan.io",
    "solscan.io", "coinmarketcap.com", "coingecko.com", "binance.com", "okx.com",
    "bybit.com", "photon-sol", "axiom.trade", "bullx", "jup.ag", "raydium",
    "t.co/", "pbs.twimg.com", "linktr.ee",
]

_cache = {}
_lock = threading.Lock()
_gate_lock = threading.Lock()
_last_fetch = [0.0]
MIN_INTERVAL = 0.35


def classify(url):
    low = (url or "").lower()
    for ig in IGNORE:
        if ig in low:
            return None
    for label, icon, keys, is_narrative in PLATFORMS:
        for k in keys:
            if k in low:
                return {"platform": label, "icon": icon, "narrative": is_narrative}
    # 其它站：只有看起来像内容页才算（有路径，不是纯首页）
    try:
        p = urllib.parse.urlparse(low if "//" in low else "http://" + low)
        if p.path and len(p.path.strip("/")) > 3:
            return {"platform": p.netloc.replace("www.", ""), "icon": "🔗",
                    "narrative": True}
    except Exception:
        pass
    return None


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_OG_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
                    re.S | re.I)
_CHARSET_RE = re.compile(r'charset=["\']?([A-Za-z0-9_\-]+)', re.I)


def _throttle():
    with _gate_lock:
        wait = MIN_INTERVAL - (time.time() - _last_fetch[0])
        _last_fetch[0] = time.time() + max(0, wait)
    if wait > 0:
        time.sleep(wait)


def fetch_title(url, timeout=5):
    """跟随跳转拿最终 URL + 页面标题。拿不到就返回 None，不抛。"""
    with _lock:
        hit = _cache.get(url)
    if hit and time.time() - hit["at"] < 6 * 3600:
        return hit["val"]

    _throttle()
    out = None
    try:
        # 推文里的外链是任何人都能写的 —— 先挡内网/回环/云元数据，
        # 再用逐跳校验的 opener，防止 302 到内网绕过首跳检查
        NG.check_outbound(url)
        opener = NG.make_safe_opener()
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "accept": "text/html,application/xhtml+xml",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "accept-encoding": "gzip, deflate",
        })
        with opener.open(req, timeout=timeout) as resp:
            final = resp.geturl()
            raw = resp.read(120000)
            enc = (resp.headers.get("Content-Encoding") or "").lower()
            try:
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                pass
            ctype = resp.headers.get("Content-Type") or ""
            charset = "utf-8"
            m = _CHARSET_RE.search(ctype)
            if m:
                charset = m.group(1)
            else:
                m = _CHARSET_RE.search(raw[:2000].decode("latin-1", "replace"))
                if m:
                    charset = m.group(1)
            try:
                html = raw.decode(charset, "replace")
            except LookupError:
                html = raw.decode("utf-8", "replace")
            title = None
            m = _OG_RE.search(html) or _TITLE_RE.search(html)
            if m:
                title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
            out = {"final_url": final, "title": (title or "")[:140] or None}
    except Exception:
        out = None

    with _lock:
        _cache[url] = {"at": time.time(), "val": out}
    return out


def collect(tweets, resolve=True, max_resolve=4):
    """从一堆推文里挖 Web2 叙事源。tweets 需要带 links 字段。"""
    seen, items = set(), []
    for t in tweets or []:
        for link in (t.get("links") or []):
            base = link.split("?")[0]
            if base in seen:
                continue
            seen.add(base)
            kind = classify(link)
            if not kind or not kind["narrative"]:
                continue
            items.append({
                "url": link, "platform": kind["platform"], "icon": kind["icon"],
                "from_handle": t.get("handle"), "from_author": t.get("author"),
                "from_url": t.get("url"), "ts": t.get("ts") or 0,
                "engagement": (t.get("likes", 0) + t.get("retweets", 0) * 2
                               + t.get("replies", 0)),
                "title": None, "final_url": None,
            })

    items.sort(key=lambda i: -i["engagement"])
    # 只解析前几条且并发数 >= 条数，保证最坏情况就是一个 timeout 的时间，不会串起来
    head = items[:max_resolve]
    if resolve and head:
        with ThreadPoolExecutor(max_workers=max(1, len(head))) as pool:
            for item, info in zip(head, pool.map(lambda i: fetch_title(i["url"]), head)):
                if info:
                    item["title"] = info.get("title")
                    item["final_url"] = info.get("final_url")

    # 平台聚合，给卡片做小结
    by_platform = {}
    for i in items:
        by_platform[i["platform"]] = by_platform.get(i["platform"], 0) + 1
    summary = [{"platform": k, "count": v}
               for k, v in sorted(by_platform.items(), key=lambda kv: -kv[1])]
    return {"items": items[:12], "summary": summary, "total": len(items)}
