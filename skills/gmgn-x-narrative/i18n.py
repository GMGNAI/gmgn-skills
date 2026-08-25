# SPDX-License-Identifier: MIT
# Copyright (c) 2026 chenjunfeng
"""中英对照表。

为什么用查表而不是在源头写双语：评分逻辑 x_narrative() 是从上游项目原样搬过来的
312 行，逐行改成 L("中","en") 会引入大量手改错误。上游走的是 DOM 级 i18n（浏览器
里逐节点替换），命令行脚本没有那个环境，所以在这里补一张表。

**漏翻会响亮地失败**，不会静默输出中文：narrative.py 的 --lang en 输出会过一遍
CJK 检查，发现残留中文就报错并列出漏掉的串。见 check_no_cjk()。
"""
import re

TRANS = {
    # ── 分项标签 ──
    "热点提及 %dh": "Hot mentions %dh",
    "硬凭据 / 名称命中": "Hard evidence / name-only",
    "打狗 KOL 提及": "Degen KOL mentions",
    "全网搜到讨论": "Found by search",
    "讨论总互动": "Total engagement",
    "项目方粉丝": "Project followers",
    "近 7 天发推": "Posts, last 7d",
    "Web2 叙事源": "Web2 narrative sources",
    "这些 KOL 累计盈利": "Cumulative KOL profit",
    "名单内其它提及": "Other mentions in list",
    "%d 条": "%d",
    # ── 结论 ──
    "叙事高峰": "Narrative peak",
    "有 Web2 叙事 + KOL 关注": "Web2 narrative plus KOL attention",
    "打狗 KOL 已下场，叙事在扩散": "Degen KOLs are in — the narrative is spreading",
    "有讨论但尚未破圈": "Some chatter, but it has not broken out",
    "项目方有基本盘，但 KOL 尚未跟进":
        "The project has a base, but no KOL has followed yet",
    "有 Web2 叙事，但链上圈子还没跟":
        "A Web2 narrative exists, but on-chain circles have not picked it up",
    "冷启动阶段": "Cold start",
    "社媒声量微弱": "Weak social presence",
    "叙事没起来": "The narrative never took off",
    "叙事高峰已过（%.0fh 前互动 %s），%dh 窗口内无人再提":
        "Peak has passed (%.0fh ago, %s engagement); nobody has mentioned it in %dh",
    "疑似自导自演": "Looks self-staged",
    "运营停摆": "Operations have stalled",
    "限流冷却中": "Rate-limit cooldown",
    "排队中": "Queued",
    # ── 项目方 ──
    "没抓到项目方 X 账号": "No project X account was obtained",
    "行情源的 twitter 字段可能指向一条推文而非账号主页":
        "the upstream twitter field may point at a post rather than a profile",
    "该账号可能未开放嵌入，或正处于 X 限流冷却":
        "the account may not allow embedding, or X is rate-limiting",
    "项目方 %s 粉丝": "Project has %s followers",
    "项目方 %s 粉丝，量级罕见": "Project has %s followers — an unusual scale",
    "项目方仅 %d 粉丝": "Project has only %d followers",
    "项目方 7 天发了 %d 条，运营活跃":
        "Project posted %d times in 7 days — actively run",
    "项目方 7 天没发推": "Project has not posted in 7 days",
    "项目方时间线不可读，仅拿到单条源推":
        "Project timeline unreadable — only the source post was obtained",
    "叙事源推：@%s": "Source post: @%s",
    "首发叙事推文": "the originating narrative post",
    "源推互动 %s": "source post engagement %s",
    "源推互动仅 %d": "source post engagement is only %d",
    # ── KOL / 提及 ──
    "%d 个链上验证的打狗 KOL 在聊": "%d on-chain-verified degen KOLs are talking",
    "%d 个打狗 KOL 提及（%s）": "%d degen KOL mentions (%s)",
    "打狗 KOL @%s 提到了": "Degen KOL @%s mentioned it",
    "打狗 KOL 池里无人提及": "Nobody in the degen KOL pool mentioned it",
    "已覆盖 %d/%d 个账号的时间线": "covered %d/%d timelines",
    "KOL 池覆盖 %d/%d": "KOL pool coverage %d/%d",
    "其余账号后台仍在预热，X 公开接口有 IP 限流":
        "the rest are still warming — X's public endpoint rate-limits by IP",
    "他们累计已实现盈利 %s —— 这批人下场通常意味着有共识":
        "their combined realized profit is %s — when this crowd shows up there is "
        "usually consensus",
    "累计已实现盈利 %s": "combined realized profit %s",
    "该地址已实现盈利 %s；单点热度容易熄火":
        "that wallet has realized %s; single-source hype burns out fast",
    "%d 个不同账号在讨论": "%d distinct accounts are discussing it",
    "不是单点刷屏": "not one account spamming",
    "全部来自同一个账号": "all from a single account",
    "叙事已经扩散到 KOL 池之外": "the narrative has spread beyond the KOL pool",
    "最新一条提及在 %.1f 小时前": "Latest mention was %.1fh ago",
    "近 6 小时有 %d 条新提及": "%d new mentions in the last 6 hours",
    "热度在升温": "attention is building",
    "%d 小时内零提及": "Zero mentions in %d hours",
    "%dh 内无人提及，热度已过": "No mentions in %dh — the moment has passed",
    "另有 %d 条历史提及（超出 %dh 窗口）":
        "%d further historical mentions (outside the %dh window)",
    "已归档，不参与打分": "archived, not scored",
    "有 %d 条历史讨论，最近一条在 %.1f 小时前 —— 按规矩不计分":
        "%d historical mentions, the most recent %.1fh ago — not scored by rule",
    "另有 %d 条疑似相关（只匹配到名称+语境词）":
        "%d more are possibly related (matched name plus context words only)",
    "没贴 CA 也没带 $符号，可能只是同名词撞车 —— 已排除在计分外":
        "no CA and no cashtag — likely a name collision, excluded from scoring",
    "名称命中来自主动搜索，计分；时间线撞词不计分":
        "name hits from an explicit search are scored; incidental timeline "
        "collisions are not",
    "命中关键词：%s": "matched keywords: %s",
    "%s 互动 · %.0fh前": "%s engagement · %.0fh ago",
    "叙事高峰在 %.0f 小时前（单条互动 %s，@%s）":
        "Peak was %.0fh ago (%s engagement on one post, @%s)",
    # ── 搜索 / Web2 ──
    "全网搜到 %d 条讨论": "Search found %d mentions",
    "全网搜到 %d 条讨论，合计互动 %s":
        "Search found %d mentions, %s engagement in total",
    "全网搜索%s": "Web search%s",
    "搜索引擎没有这个 CA 的收录": "Search engines have no coverage of this CA",
    "搜索引擎对脚本流量敏感，结果会在下次查询同一个 CA 时补上":
        "search engines throttle script traffic; results usually fill in on the next "
        "query for the same CA",
    "搜索结果里剔掉了 %d 条不相关的": "%d irrelevant results were discarded",
    "水化后用同一套强框定规则做了二次校验":
        "re-validated with the same strict framing rules after hydration",
    "没找到 Web2 叙事源": "No Web2 narrative source found",
    "推文外链里没有小红书/微博/抖音/新闻这类站外内容":
        "no off-site links (Xiaohongshu / Weibo / Douyin / news) in the posts",
    "有 Web2 叙事背书：%s": "Backed by Web2 narrative: %s",
    "叙事归类：%s": "Narrative type: %s",
    # ── 长句 ──
    "X 对爬虫基本封闭，搜索引擎的 0 结果**推不出「没人聊」**"
    "——要判断真实声量请直接在 X 站内搜索。"
    "本项只按已抓到的证据打分，不因搜不到而扣分":
        "X is effectively closed to crawlers, so zero search results **do not mean "
        "nobody is talking** — search inside X to judge real volume. This skill scores "
        "only the evidence it did find and never deducts for a miss.",
    "X 叙事 & 讨论度": "X narrative & chatter",
}

_lang = ["zh"]
_missing = set()


def set_lang(v):
    _lang[0] = "en" if v == "en" else "zh"


def T(zh):
    if _lang[0] == "zh":
        return zh
    out = TRANS.get(zh)
    if out is None:
        _missing.add(zh)
        return zh
    return out


CJK = re.compile(r"[一-鿿　-〿＀-￯]")


def check_no_cjk(text, allow=()):
    """英文模式下不该有中文残留。漏翻必须响亮地失败，而不是静默输出中文。

    `allow` 是豁免串 —— 代币自己的名字（「梭子蟹币」这种）本来就不该翻译，
    把它算成漏翻会让守卫天天误报，久而久之就没人看它了。
    """
    if _lang[0] != "en":
        return []
    bad = []
    for ln in text.split("\n"):
        probe = ln
        for a in allow:
            if a:
                probe = probe.replace(a, "")
        if CJK.search(probe):
            bad.append(ln)
    return bad


def missing():
    return sorted(_missing)
