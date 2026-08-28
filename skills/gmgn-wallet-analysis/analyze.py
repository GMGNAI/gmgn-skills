#!/usr/bin/env python3
"""
gmgn-wallet-analysis — the four-gate wallet dossier.

Answers one question: "this wallet's numbers look good — should I actually copy it,
and if I do, what happens to me?"

Four gates, each pass/fail, each with the number that decided it:
  G1 AUTHENTICITY  is the record real, or one lucky coin / a dev marking its own homework?
  G2 CURRENCY      is the edge still working THIS week, or is the good number historical?
  G3 REACHABILITY  can you actually get filled — copy window, entry band, trade size?
  G4 SURVIVABILITY does it cut losses, or does it ride things to zero and take you along?

Verdict is a function of the gates, not a black-box score.

Usage (live):
    python3 analyze.py <wallet> <chain> [zh|en] [--latency <sec>] [--size <usd>]
Usage (offline, for verification):
    python3 analyze.py --fixture fixtures/<name>.json [zh|en]

Read-only. Never signs, never trades.
"""

import json
import os
import statistics
import subprocess
import sys
import time

# ─────────────────────────── plumbing ───────────────────────────



# ─── language ────────────────────────────────────────────────────────────────
# English is the source of truth: every user-facing string in this file is written in
# English, and the `ZH` table below maps an English template to its translation. A key that
# is missing from the table falls back to English, which is always a correct answer — so a
# partial translation degrades into mixed language, never into a crash or a blank line.
#
# Templates use positional placeholders (`{0}`, `{1}`) rather than named ones, because the
# same value often reads in a different position in another language and the translator
# needs to be able to move it.
ZH = {
    "⚠️ Its last trade was {0} ago — every figure here describes a wallet that has since gone quiet.": "⚠️ 它最后一笔成交在 {0}前 —— 这里所有数字描述的都是一个已经安静下来的钱包。",
    "Last trade {0} ago.": "最后一笔成交在 {0}前。",
    "⚠️ A track record is past behaviour. It is not a forecast, and none of this is advice — size it yourself.": "⚠️ 战绩只反映已经发生的操作，不代表未来收益。仓位自己定，风险自己担。",
    "only {0:,} lost more than half": "亏超一半的只有 {0:,} 个",
    "{0:,} of {1:,} coins in profit": "{1:,} 个币里 {0:,} 个在赚",
    "This wallet trades by {0}": "这个钱包{0}",
    "This wallet has lost {0} {1}, {2}": "这个钱包{1}{2}，累计亏了 {0}",
    "This wallet has made {0} {1}, {2}": "这个钱包{1}{2}，累计赚了 {0}",
    "so far": "到目前为止",
    "over {0:.0f} days": "在过去 {0:.0f} 天里",
    "trading steadily across a wide book": "靠一个很宽的盘面稳定出货",
    "getting into small caps early": "靠早早进小盘",
    "picking a few coins and sizing into them": "靠选中几个币然后加到重仓",
    "turning over volume at machine speed": "靠机器速度高频周转",
    "outrunning everyone into small caps": "靠机器速度抢在所有人前面进小盘",
    "Even at its own pace, anything over {0} moves the price against you.": "就算跟得上它的节奏，超过 {0} 的单子也会把价格推到你自己脸上。",
    " — a pace a person can actually match": " —— 这个节奏人跟得上",
    " — nobody is out-typing that": " —— 手速这块，人拼不过",
    "in and out inside {0}": "进出不超过 {0}",
    "it hunts around {0}": "它专打 {0} 上下的盘子",
    "{0} — about {1:.0f}x its long-run pace": "{0} —— 比长期均速快 {1:.0f} 倍",
    "{0} follow it for a week and {1} becomes {2} ({3})": "{0} 跟它一周，{1} 变 {2}（{3}）",
    "only {0} lost more than half": "亏超一半的只有 {0} 个",
    "{0} banked so far, ": "累计落袋 {0}，",
    "{0} of the {1:,} coins it traded are in profit": "它打过的 {1:,} 个币里，{0} 个现在是赚的",
    "The bar to clear: {0}.": "门槛在这：{0}。",
    "and anything over {0} moves the price against you": "而超过 {0} 的单子会把价格推到你自己脸上",
    "it enters around {0}": "它在市值 {0} 附近进",
    "it is gone in {0}": "它 {0}就走",
    "and ": "而且",
    "but ": "但",
    " · {0}": " · {0}",
    "it lost {0} itself": "它自己这周亏掉 {0}",
    "it banked {0} itself": "它自己这周落袋 {0}",
    "{0} in one week: {1} following it becomes {2}": "一周 {0}：{1} 跟着它走会变成 {2}",
    "Read the data gap below and fix what it names, then re-run.": "看下面的数据缺口，按它写的原因处理，然后重跑。",
    "Its activity sample is too thin to judge reachability — this wallet barely trades, so there is nothing to fix. Watch it until it does.": "它的交易记录太少，判断不了你能不能吃到 —— 这个钱包几乎不交易，没什么可补的。等它动起来再看。",
    " — sparse: {0} rows stretched over {1:.0f} days": " —— 稀疏：{0} 条记录摊在 {1:.0f} 天里",
    "measured across {0:.0f} days of its trades, not just this week": "这个窗口是拿它 {0:.0f} 天的交易算出来的，远不止报告的 7 天窗口",
    " (these buys span {0:.0f} days, so this is its habit, not this week)": "（这些买入横跨 {0:.0f} 天，远超报告的 7 天窗口，是它一贯的习惯）",
    "holdings refused: the private key IS configured, but its signature was rejected: {0} — check GMGN_PRIVATE_KEY holds the full PEM (BEGIN/END lines included, no stray whitespace) and that it is the key paired with this GMGN_API_KEY. Adding the variable again will not help. Profit concentration falls back to bucket inference; live book and honeypot check missing": "holdings 被拒：私钥**已经配了**，但签名没通过：{0} —— 检查 GMGN_PRIVATE_KEY 里是不是完整 PEM（含 BEGIN/END 两行、没有多余空格），以及它是否和这个 GMGN_API_KEY 配对。再加一遍这个变量没有用。利润集中度改用盈亏桶推断，当前持仓与蜜罐检查缺失",
    "the money is spread across many coins (top 3 = {0}), so no single copy decides it": "钱摊在很多币上（前 3 个只占 {0}），单独跟中哪一笔都不决定结果",
    "{0} of the money came from just 3 coins — copying it randomly mostly misses them": "{0} 的钱只来自 3 个币 —— 随机跟单大概率跟不到这几个",
    "wide enough to place by hand, if you are watching": "这个窗口手动下单来得及，前提是你在盯",
    "under a minute — you need automated copy-trading for this; clicking by hand you will not make it": "不到一分钟 —— 这个节奏得用自动跟单，手点是赶不上的",
    ", bought at {0} mcap": "，买在市值 {0}",
    "{0} banked so far — ": "累计落袋 {0} —— ",
    "as a copy that is {0} → {1}": "折算成跟单是 {0} → {1}",
    "{0} over the last 7 days": "近 7 天 {0}",
    "It lost {0} this week": "这一周它亏掉 {0}",
    "It banked {0} this week": "这一周它落袋 {0}",
    ", {0}{1}, holds for {2} typically": "，{0}{1}，持仓通常 {2}",
    "no open position is in profit, so concentration says nothing here": "当前持仓没有一个是赚的，集中度在这里说明不了什么",
    "current book is {0} concentrated ({1} open of {2:,} traded, so this says nothing about the closed record)": "当前持仓集中度 {0}（{1} 个在手 / 共打过 {2:,} 个，说明不了已平仓的部分）",
    "See the first gate below for what failed.": "具体没过哪一条，看下面第一道闸门。",
    "NO READ · the track record did not check out": "看不出来 · 战绩没通过核验",
    "DO NOT COPY · one position carried the whole result": "别跟 · 全靠一个仓位撑起来的",
    "{0} of the {1:,} coins it traded are in profit, and only {2} lost more than half": "它打过的 {1:,} 个币里，{0} 个现在是赚的，只有 {2} 个亏超一半",
    "{0:,} tokens, {1:,} in profit, {2}, {3}": "{0:,} 币 · {1:,} 个在赚 · {2} · {3}",
    " ({0:,} bought and not yet sold, so they have no realized result)": "（其中 {0:,} 个买了还没卖，没有已实现结果）",
    "{0} win rate on what it has sold": "卖掉的部分胜率 {0}",
    "wallet is {0:.0f} days old": "钱包开了 {0:.0f} 天",
    "it does not cut losses": "它不砍仓",
    "you cannot keep up": "你跟不上",
    "not earning now": "现在不赚了",
    "record may be faked": "战绩可能是刷的",
    "was good, not any more": "以前很强，现在不行了",
    "it lost {0} itself this week": "它自己这周亏了 {0}",
    "7-day backtest: {0} following it → {1} ({2} in one week)": "近 7 天回测：{0} 跟着它走 → {1}（一周 {2}）",
    " — {0} banked": " —— 累计落袋 {0}",
    "{0} of the {1:,} coins it traded made money, and only {2} lost more than half": "它打过的 {1:,} 个币里，{0} 个赚钱，只有 {2} 个亏超一半",
    "{0} traded, {1} of them lost money — {2} gone in total": "打了 {0}，其中 {1} 个是亏的 —— 总共亏掉 {2}",
    "{0:,} coins": "{0:,} 个币",
    "anonymous address": "匿名地址",
    "unremarkable": "平平无奇",
    "solid": "稳",
    "seriously good": "真高手",
    "top-tier record": "顶级战绩",
    "loses money": "亏钱的号",
    "record unreadable": "战绩读不出来",
    "{0:,} tokens, {1} profitable ({2}), {3}": "{0:,} 币 · {1} 盈利（{2}）· {3}",
    "{0} realized all-time — ": "累计落袋 {0} —— ",
    "it has traded {0:,} coins, {1} of them profitably": "交易过 {0:,} 个币，{1} 是赚钱的",
    "Data pull failed, no verdict possible: {0}\nCheck `gmgn-cli config --check` first; on 429 wait for the stated reset; on 401/403 with valid credentials check IPv6 (gmgn-cli is IPv4 only).": "取数失败，无法出结论：{0}\n先确认 gmgn-cli config --check 通过；429 请按提示的 reset 时间再试；401/403 且凭证正确时先排查 IPv6（gmgn-cli 只走 IPv4）。",
    "  BOUGHT IN THE LAST 24H": "  它 24 小时内刚买了",
    "  HOW TO FOLLOW": "  怎么跟",
    "  WHAT TO DO": "  怎么办",
    "  bought in 24h: ": "  24h 买入：",
    "  live book: unavailable (see data gaps)": "  持仓：未取到（见数据缺口）",
    "  profit concentration {0} (largest winner's share of all gains)": "  利润集中度 {0}（最大盈利仓位占全部盈利）",
    "  {0} positions · {1} total": "  持仓 {0} 个 · 合计 {1}",
    "  {0} {1} · 24h bought {2} / sold {3}": "  {0} {1} · 24h 买 {2} / 卖 {3}",
    " (hit page cap — busiest slice only)": "（触到分页上限，只覆盖最活跃的一段）",
    " ({0})": "（{0}）",
    " over {0}": "，历时 {0}",
    " · fees {0} = {1} of profit": " · 手续费 {0}（{1}）",
    " · your {0} = {1:.1f}x its clip": " · 你的 {0} = 它单笔的 {1:.1f} 倍",
    " · {0} on paper": " · 浮盈 {0}",
    " — {0} realized all-time": " —— 累计落袋 {0}",
    " ≈ {0} of profit": " ≈ 吃掉利润 {0}",
    " ≈ {0} of profit (estimated)": " · 手续费约 {0}（估算）",
    ", ": "、",
    "1d {0} · 7d {1} · 30d {2} · all {3}": "1d {0} · 7d {1} · 30d {2} · 全期 {3}",
    "1–7 days": "1 – 7 天",
    "7-day backtest: {0} following it → {1}": "近 7 天回测：{0} 跟着它走 → {1}",
    "7d {0}": "7d {0}",
    "7d {0} + {1}": "7d {0} + {1}",
    "< 24h": "< 24 小时",
    "< 60s": "< 60 秒",
    "> 7 days": "> 7 天",
    "AUTHENTICITY": "真实性",
    "Are the contracts on {0} safe — honeypot, liquidity, mint authority?": "{0} 的合约安全吗 —— 有没有貔貅、流动性够不够、增发权限在谁手上？",
    "BullX user": "BullX 用户",
    "CLEARED": "已排除",
    "COPY THE BUYS, NOT THE EXITS · it does not cut losses": "跟买可以，跟卖不行 · 它不砍仓",
    "COPYABLE AT SMALL SIZE · all four pass": "可以小仓跟 · 四项全过",
    "CURRENCY": "时效性",
    "Check back in a week to see whether it is still running this hot?": "一周后再看一次，它还这么热吗？",
    "Check the chips on these coins yourself before following. All of this measures behaviour that already happened — not a prediction, not advice.": "跟单前请自己查一遍这几个币的筹码。以上全部是已发生行为的度量，不是预测，也不是投资建议。",
    "Come back when it has done it again on other tokens.": "等它在更多币上再赚一次，再回来看。",
    "Configure GMGN_PRIVATE_KEY and re-run. Do not size off this record first.": "配好 GMGN_PRIVATE_KEY 再跑一次。核验前别按这份战绩下注。",
    "Confirm the chain: base58 → sol, 0x → bsc/base/eth.": "确认链选对了：base58 → sol，0x → bsc/base/eth。",
    "Confirm this is a wallet, not a token contract — a contract queries fine and returns zeros everywhere, which looks like an answer and is not one.": "确认这是钱包地址而不是代币合约（代币合约也能查通，但每项都返回 0，看起来像答案，其实不是）。",
    "Confirm this is a wallet, not a token contract. If it is a wallet, wait for real trades.": "先确认你给的是钱包地址而不是代币合约；如果确实是钱包，等它有真实买卖记录再看。",
    "Copying it is a race on latency, not on judgement": "跟单要拼手速，人手做不到",
    "DATA GAPS (unevaluated ≠ passed):": "数据缺口（未评估 ≠ 通过）：",
    "DATA GAPS:": "数据缺口：",
    "DO NOT COPY · it has stopped making money": "别跟 · 它最近已经不赚了",
    "DO NOT COPY · it is a launcher trading its own tokens": "别跟 · 它是发币方，赚的是自己发的币",
    "DO NOT COPY · one token made all the money": "别跟 · 全靠一个币赚钱，复制不了",
    "DO NOT COPY · the profit is self-dealt": "别跟 · 它的盈利是自己刷出来的",
    "DO THIS  ": "怎么办  ",
    "Do not mirror it. Treat it as a signal source: note what and at what mcap, then enter on your own terms.": "别抄单。把它当信号源：它买什么、在什么市值买，自己二次筛选后按自己的节奏进。",
    "Do not read its trading — what matters is how many of the tokens it launched survived. Want me to look at its launch record?": "别看它的交易能力 —— 关键是它发过的币活下来几个。需要我帮你查它的发盘记录吗？",
    "Do not read its trading. Check how many of its launches survived (gmgn-wallet-score).": "别看它的交易能力，去查它发的币活下来几个（gmgn-wallet-score）。",
    "EVIDENCE": "判断依据",
    "Every claim above is backed by a number. Below: what each of the four checks tested, and the number that decided it.": "上面每一个结论都有数据支撑。下面是四项检查各自查了什么，以及决定它的那个数。",
    "Every claim above is backed by a number. The evidence is below: what each of the four checks actually tested, and the raw figures.": "上面每一个结论都有数据支撑。判断依据在下面：四项检查各自查了什么，以及全部原始数字。",
    "Everything above measures behaviour that already happened. Not a prediction, not advice.": "以上全部是已发生行为的度量，不是预测，也不是投资建议。",
    "Fill in the missing data first — usually by configuring GMGN_PRIVATE_KEY.": "先补数据（通常是配置 GMGN_PRIVATE_KEY），再决定。",
    "First confirm this is a wallet, not a token contract. Three checks below.": "先确认这是钱包地址，不是代币合约。下面有三步检查。",
    "For 0-100 scores and a latency/slippage backtest, use gmgn-wallet-score.": "要 0–100 评分和延迟/滑点回测，接 gmgn-wallet-score",
    "GMGN flags it as {0} — {1}": "GMGN 标记「{0}」—— {1}",
    "GMGN flags this wallet as {0}, and it cannot be checked (holdings unavailable) — the {1} in this window is neither confirmed nor refuted. Configure GMGN_PRIVATE_KEY and re-run": "GMGN 标记「{0}」，但无法核验（holdings 不可用）—— 这 7 天 {1} 的盈亏既没被证伪也没被证实，配好 GMGN_PRIVATE_KEY 后重跑",
    "GMGN flags this wallet as {0}, and the local check agrees: only {1} of realized gains came from positions netting more than their own cost basis — the rest is round-tripped volume. The {2} realized P&L cannot be taken at face value": "GMGN 标记「{0}」，且本地核验支持它：只有 {1} 的已实现盈利来自净赚超过自身成本的仓位，其余是来回对敲的量。这 7 天 {2} 的已实现盈亏不可采信",
    "GMGN user": "GMGN 用户",
    "GMGN's label, refuted locally: {0} of realized gains came from positions netting more than their own cost basis — self-dealing cannot produce that": "GMGN 的标记，核验不成立：{0} 的盈利来自净赚超过自身成本的仓位",
    "GMGN's own positive marker": "GMGN 官方正向标记",
    "Get a live quote before sending — want me to price it?": "下单前先看实时报价 —— 需要我帮你查吗？",
    "HOLD OFF · a wash-trading flag we cannot check": "先别动 · 有刷量嫌疑，但查不了",
    "HOLD OFF · one of the four was not measured": "先别动 · 四项里有一项没测到",
    "If it is a wallet, check whether it only ever received transfers or airdrops rather than trading. Want me to look at what it holds?": "如果确实是钱包，要看它是不是只收过转账/空投而没真交易过。需要我帮你看它持有什么吗？",
    "If it is a wallet, use gmgn-portfolio holdings to see whether it only ever received transfers or airdrops.": "确认是钱包后，用 gmgn-portfolio holdings 看它是否只收过转账/空投。",
    "If you copy it, your order must land within {0} of its buy — otherwise skip the trade.": "如果要跟，你的下单要落在它买入后 {0}以内，否则不要进。",
    "If you had followed it with {0} seven days ago": "如果 7 天前跟了它 {0}",
    "If you want this scored 0-100 with your own latency and slippage modelled in, want me to run that backtest?": "想要 0–100 打分、并把你自己的延迟和滑点算进去，需要我帮你跑一遍回测吗？",
    "Is this address a wallet at all, or a token contract?": "这个地址到底是钱包还是代币合约？",
    "It bought {0} in the last 24h — run gmgn-token / gmgn-holder-analysis on those before following it in.": "先用 gmgn-token / gmgn-holder-analysis 查 {0} 的筹码，别只因为它买了就买",
    "It bought {0} in the last 24h. Worth checking the holder structure on those first — who is holding, at what cost, and whether the contract is safe. Want me to analyse them?": "它 24 小时内买了 {0}。建议先看这几个币的筹码结构 —— 谁在持有、成本多少、合约是否安全。需要我帮你分析吗？",
    "It holds {0} coins — list the whole book with costs?": "它持有 {0} 个币，把完整持仓和成本列出来看看？",
    "It is still holding {0} coins worth {1} — biggest is {2} at {3}.": "它手上还压着 {0} 个币、共 {1} —— 最大一笔 {2} {3}。",
    "It is still holding {0} coins worth {1} — biggest is {2} at {3}. Not a wallet that only churns.": "它手上还压着 {0} 个币、共 {1} —— 最大一笔 {2} {3}。不是只刷量的号。",
    "It is still holding {0} coins — which of those has it not sold yet?": "它还持有 {0} 个币，哪些是还没卖的？",
    "It launched {0} tokens — how many of them are still alive?": "它发盘情况怎么样 —— 发过 {0} 个币，现在还活着几个？",
    "Its money is historical. Re-run this in 7 days to see whether form recovers or keeps sliding.": "它的钱是过去赚的。7 天后再跑一次这份分析，看是回暖还是继续退。",
    "Its profit figures are not trustworthy — treat the track record as unknown": "它的盈利数字不可采信 —— 把这份战绩当作未知",
    "KOL": "KOL",
    "MEV bot": "MEV 机器人",
    "Maestro bot user": "Maestro 用户",
    "NEXT": "下一步",
    "NO CARD  ": "无决策卡  ",
    "NO READ · no trades in 7 days": "看不出来 · 这 7 天没有交易",
    "NO READ · only {0} tokens traded": "看不出来 · 只交易过 {0} 个币",
    "Note what it buys and at what market cap, then enter on your own terms.": "看它买什么、在什么市值买，然后按你自己的节奏进。",
    "P&L": "盈亏",
    "P&L may be self-dealt, not market-earned": "盈亏可能来自自我对敲，不是市场收益",
    "PepeBoost user": "PepeBoost 用户",
    "Photon user": "Photon 用户",
    "Quote through gmgn-swap before sending.": "下单前先用 gmgn-swap 看报价。",
    "REACHABILITY": "可及性",
    "Re-run in 7 days to see whether it recovers or keeps sliding.": "7 天后再跑一次，看是回暖还是继续掉。",
    "SURVIVABILITY": "生存性",
    "Score it 0-100 with my own latency and slippage modelled in?": "跟单评分：给它打个 0–100 分，把我自己的延迟和滑点算进去？",
    "Set your own stop — it does not cut, and riding it to the end means riding it to zero.": "自己设止损 —— 它不砍仓，你跟到底就是陪它归零。",
    "Start at ≤ {0} (it averages {1} per buy; above its own size your slippage is worse than its). Quote through gmgn-swap before sending.": "起步规模 ≤ {0}（它自己单笔均 {1}；超过它的单笔规模，你的滑点会比它差）。下单前用 gmgn-swap 看报价。",
    "Start at ≤ {0}, landing within {1} of its buy.": "起步 ≤ {0}，下单要在它买入后 {1}以内。",
    "Start at ≤ {0}.": "起步 ≤ {0}。",
    "THE FOUR GATES": "四道闸门",
    "Take its entries and keep your own stop. Do not wait for it to sell first.": "跟它进场，止损用你自己的。别等它先卖。",
    "The 0-200% band is not a win count. It holds {0} tokens while the win rate implies about {1} winners — the other {2} were bought and have no realized result yet, so they sit at 0% inside that band. Read the win rate for how often it wins, and this chart only for the shape of the tail.": "0–200% 这一档不是「赢了多少个」。它装了 {0} 个币，而胜率隐含的赢家只有约 {1} 个 —— 另外 {2} 个是买了还没卖、没有已实现结果，所以停在这一档的 0% 边缘。想知道它多久赢一次看胜率，这张图只看尾部形状。",
    "The sample is too small for any ratio to hold. Watchlist it until it has traded 5.": "样本太小，任何比率都不成立。加观察名单，满 5 个币再看。",
    "This is a launcher, so its trading record is partly self-authored. What matters is how many of its own tokens survived and how they behaved. Want me to look at its launch record?": "这是个发币方钱包，它的战绩有一部分是自己写的。关键是它发的币活下来几个、表现如何。需要我帮你查它的发盘记录吗？",
    "This is a launcher. Do not score its trading — check its launch survival and security record (gmgn-wallet-score, Dev angle).": "这是发币方。别评估它的“交易能力”，去查它历史发币的毕业率和安全性（gmgn-wallet-score 的 Dev 角度）。",
    "Treat its P&L as if it were not there. Watch what it buys; do not use these numbers.": "当它的盈亏数字不存在。想看它买什么可以，别拿这个当依据。",
    "Use it only as a signal of what to look at. If you enter, set your own stop.": "只当信号源看它买什么。真要自己进，止损必须你自己设。",
    "WATCH, DO NOT COPY · you cannot get its fills": "能看不能抄 · 你抢不到它的价",
    "WATCH, DO NOT COPY · you cannot get its fills, and it never cuts": "能看不能抄 · 你抢不到它的价，它也不砍仓",
    "What do the chips look like on {0} — who is holding, and at what cost?": "{0} 的筹码分析 —— 谁在持有、成本多少？",
    "What shape is {0} in right now — still climbing, or already breaking down?": "{0} 的走势和形态怎么样 —— 还在涨，还是已经开始崩？",
    "Whatever size you use, keep it at or under {0} — half of the {1} this wallet puts on a buy. Past its own size your fill is worse than the ones its record was built on, so its numbers stop describing you.": "无论你打算下多大，都压在 {0} 以内 —— 那是它单笔 {1} 的一半。超过它自己的规模，你的成交价就比撑起这份战绩的那些差，它的数字对你不再成立。",
    "Which coins actually made this week's money?": "这一周的钱到底是哪几个币赚的？",
    "Who else is buying {0} — any smart money or KOLs in there?": "还有谁在买 {0} —— 里面有聪明钱或 KOL 吗？",
    "You would need to land inside {0} — not achievable by hand": "你要在 {0}内落单才可能吃到，人手做不到",
    "__clause_separator__": "，",
    "__list_separator__": "、",
    "a caller — you are probably not the first one in": "它在公开喊单，你大概不是第一个进的",
    "a public identity with {0:,} followers trading small caps — copy flow has already moved the price before your order": "公开身份 {0:,} 粉丝且主打小市值 —— 跟单盘在你之前就已经推过价",
    "account": "账号",
    "accumulating": "在建仓",
    "active winner": "P小将",
    "active, but it has not turned into anything": "有在做，但没做出结果",
    "activity empty — copy window, entry band and scale-in/out shape were not evaluated": "activity 为空 —— 可跟窗口、入场市值带、加仓/出货姿势本次均未评估",
    "activity sample too thin — reachability not evaluated": "activity 样本不足，可及性未评估",
    "all time": "全期",
    "all {0}": "全期 {0}",
    "almost never trades, and lands it when it does": "极少出手，出手就中",
    "also bought in 24h": "24 小时内还买了",
    "an information edge you cannot replicate": "信息优势不可复制",
    "average buy {0} — thin enough that fees and slippage eat the edge": "平均单笔买入 {0} —— 边际薄到手续费和滑点就吃掉了",
    "badly down": "重伤",
    "band": "区间",
    "bleeding out": "连败突击兵",
    "blue-verified": "蓝V",
    "bluechip holder": "蓝筹持有者",
    "bot-tier, unfollowable": "机器级，跟不动",
    "both 7d and 30d are negative ({0} / {1})": "近 7d 和 30d 都是负的（{0} / {1}）",
    "bought in 24h": "24 小时内买入",
    "broken down": "崩坏",
    "builds its position in the launch block": "与发币方同区块建仓",
    "bundler": "打包买入",
    "busy hands that keep the money": "手勤、赚得住，典型的活跃盈利户",
    "bystander": "观望者",
    "cadence": "节奏",
    "can you get filled": "你吃得到吗",
    "cannot tell": "无法判断",
    "charging in fast with a heavy tail of big losses": "高频硬冲，重亏占比高",
    "conclusion": "结论",
    "cooling off": "退潮",
    "copy flow already moved the price; your slippage is worse": "跟单盘已推过价，你的滑点更差",
    "copy window {0}": "可跟窗口 {0}",
    "copy window {0} (your latency budget {1})": "可跟窗口 {0}（延迟预算 {1}）",
    "cost": "成本",
    "cost {0} · {1} sells": "成本 {0} · 卖 {1} 次",
    "cuts losses": "会砍仓",
    "d": " 天",
    "deep underwater": "深套户",
    "distributing": "在出货",
    "does it cut losses": "它会砍仓吗",
    "does not cut": "不砍仓",
    "earning now": "现在在赚",
    "engine": "利润引擎",
    "enters far too early for you to match its price": "极早入场，你拿不到同价",
    "entry": "入场",
    "entry mcap p25/p50/p75 = {0}/{1}/{2}": "入场市值 p25/p50/p75 = {0}/{1}/{2}",
    "entry mcap p25/p50/p75 = {0}/{1}/{2} · {3} of entries under $100k": "入场市值 p25/p50/p75 = {0}/{1}/{2} · {3} 的入场在 $100K 以下",
    "entry {0}": "入场 {0}",
    "fee donor": "手续费贡献者",
    "fees took {0} of the profit ({1} paid vs {2} realized), leaving {3} net per trade — no room for your slippage": "手续费吃掉了利润的 {0}（实付 {1} vs 已实现 {2}），单笔只剩 {3} —— 你的滑点没有空间",
    "flash flipper": "秒杀流",
    "flat": "打平",
    "form": "手感",
    "fresh wallet": "新钱包",
    "friction": "摩擦",
    "friction eats the bulk": "摩擦吃掉大头",
    "friction manageable": "摩擦可控",
    "full-auto grinder": "全自动P机",
    "funded from {0}": "启动资金来自 {0}",
    "gas burner": "烧Gas机",
    "gas is an estimated {0} of the profit ({1:,} trades × {2} ≈ {3} vs {4} realized), leaving {5} net per trade — no room for your slippage": "估算 gas 吃掉利润的 {0}（{1:,} 笔 × 均 {2} ≈ {3} vs 已实现 {4}），单笔净赚只有 {5} —— 你的滑点没有空间",
    "get your order in within": "下单要在它买入后",
    "get your order in within {0} of its buy": "下单要在它买入后 {0}以内",
    "h": " 小时",
    "harvester": "收割机",
    "has held assets that survived": "持有过存活下来的资产",
    "heating up": "升温",
    "heavily followed": "被大量跟单",
    "heavy-loss share {0} ({1:,}/{2:,} down >50%)": "重亏 {0}（{1:,}/{2:,} 亏超 50%）",
    "high freq, needs tooling": "高频，需脚本",
    "high frequency and strongly profitable — the strongest cell": "高频且强盈，这一格最强",
    "high frequency, high friction; the loss is mostly cost": "高频高摩擦，净亏主要亏在成本",
    "holding": "持仓",
    "holdings came back empty — live book, profit concentration and the honeypot check were all skipped": "holdings 返回空 —— 当前持仓、利润集中度、蜜罐检查均未评估",
    "holdings failed: {0} — profit concentration falls back to bucket inference; live book and honeypot check missing": "holdings 取数失败：{0} —— 利润集中度改用盈亏桶推断，当前持仓与蜜罐检查缺失",
    "holdings refused by the rate limiter (not an auth problem): {0} — profit concentration falls back to bucket inference; live book and honeypot check missing. Re-run once the limit resets.": "holdings 被限流拒绝（不是鉴权问题）：{0} —— 利润集中度改用盈亏桶推断，当前持仓与蜜罐检查缺失，等限流恢复后重跑即可",
    "holdings unavailable (needs GMGN_PRIVATE_KEY / critical auth): {0} — profit concentration falls back to bucket inference; live book and honeypot check missing": "holdings 不可用（需要 GMGN_PRIVATE_KEY 的 critical auth）：{0} —— 利润集中度改用盈亏桶推断，当前持仓与蜜罐检查缺失",
    "honeypot flag checked on {0} positions, none hit": "查了 {0} 个持仓的蜜罐标记，无命中",
    "honeypot flag checked on {0} positions: {1} hit ({2}) but each is refuted by its own fill history — one has {3:,} completed sells, and a honeypot cannot be sold. These are transfer-restricted tokenised-stock / RWA contracts — false positives": "已检查 {0} 个持仓的蜜罐标记：{1} 个命中（{2}）但都被自己的成交记录否掉 —— 其中一个已卖出 {3:,} 次，蜜罐是卖不出去的，这批是转账受限的代币化股票/RWA，误报",
    "hunts on {0}": "打 {0}",
    "identity keeps churning; past reputation does not carry": "身份在洗，历史声誉不可延续",
    "insider": "内幕关联",
    "intraday": "日内流",
    "is it still earning now": "现在还在赚吗",
    "is the data trustworthy": "数据可信吗",
    "it cuts losses": "它会砍仓",
    "it does not ride positions to zero": "不会拿着亏损仓位到归零",
    "it has traded {0} coins, {1} of them profitably": "它交易过 {0} 个币，{1} 是赚钱的",
    "it made {0} itself this week": "它自己这周赚了 {0}",
    "its 3 best coins made {0} of the money": "最赚的 3 个币赚走了 {0} 的钱",
    "its fills are reachable at your speed": "它的价位你抢得到",
    "its profit comes from sandwiching orders like yours": "它的收益来自夹你这类订单",
    "key numbers": "关键数字",
    "large cap, deep": "大市值，容量足",
    "last trade {0} ago": "最后一笔在 {0}前",
    "last trade {0} ago — every figure here describes a wallet that has since gone quiet": "最后一笔在 {0}前 —— 上面所有数字描述的是一个此后已经安静下来的钱包",
    "launched {0} tokens": "发过 {0} 币",
    "launched {0} tokens ({1} graduated · {2})": "发过 {0} 币（毕业 {1} · {2}）",
    "launcher wallet — this measures its handling of its own token, so it does not apply": "发币方钱包，该项衡量的是它对自己代币的操作，不成立",
    "launcher wallet: created {0} vs traded {1} — its win rate and entry timing are self-authored, not a market read": "发币方钱包：自己发了 {0} 个币 / 交易过 {1} 个 —— 胜率和入场时机是自己写的，不是市场读出来的",
    "live book: unavailable (see data gaps)": "持仓：未取到（见数据缺口）",
    "long hold": "长持流",
    "low freq, slow evidence": "低频，样本慢",
    "lukewarm": "温吞户",
    "m": " 分",
    "machine cadence and still strongly profitable": "机器级频次还能稳定强盈，跟不上，只能看",
    "machine cadence plus broad heavy losses": "机器级频次配大面积重亏，策略已失效",
    "made {0} in that week": "这一周赚了 {0}",
    "market value": "市值",
    "marks": "特征",
    "mean is usable": "均值可用",
    "mean {0} · median copy window {1} ({2} round trips)": "均 {0} · 窗口中位 {1}（{2} 回合）",
    "meaningful friction": "摩擦不小",
    "median copy window {0} against your {1} latency — under 3x margin, it is likely already selling when you land": "可跟窗口中位 {0}，你的延迟 {1} —— 余量不足 3 倍，你买进去的时候它大概已经在卖了",
    "median entry mcap {0} — sniper/pre-graduation territory; you enter at 5–10x its cost": "它一般在市值 {0} 就进了 —— 币还没上公开池，你能买到的时候价格已经是它成本的 5–10 倍",
    "median entry mcap {0} — sniper/pre-graduation territory; you enter at 5–10x its cost. {1} of its entries are under $100k": "它一般在市值 {0} 就进了 —— 币还没上公开池，你能买到的时候价格已经是它成本的 5–10 倍；它 {1} 的买入都在 $100K 以下",
    "median entry {0}": "入场中位 {0}",
    "metric": "维度",
    "mid cap, copyable": "中市值，可跟",
    "money printer": "印钞机",
    "most of its coins are down more than 50%": "半数以上币亏超 50%",
    "net negative": "净亏",
    "net positive": "净盈",
    "never worked": "长期亏",
    "no 7d return — the headline figure cannot be computed": "拿不到 7 天收益，头条数字算不出来",
    "no X account bound (no public identity on GMGN)": "没有绑定 X 账号（GMGN 上查不到公开身份）",
    "no X account bound and no traceable funding source — an anonymous address": "没有绑定 X 账号，也没有可查的资金来源 —— 匿名地址",
    "no buys or sells in 7 days — nothing to evaluate": "7 天内没有买卖记录，无从评估",
    "no high-severity flags": "无高危旗标",
    "no high-severity flags — but honeypots and the live book were not checked": "无高危旗标，但蜜罐与当前持仓未检查（holdings 不可用）",
    "no history to check": "没有可供检验的历史",
    "no reachability obstacle found": "未发现可及性障碍",
    "no single profit engine — following it means following the whole book, not any one trade": "没有单一利润引擎，跟它等于跟它的整个组合，不是跟某一笔",
    "no trades in the window": "数据区间内没有交易",
    "normal cadence, positive return, no glaring weakness": "常规频次、正收益，无明显短板",
    "normal, hand-tradeable": "常规，可手动",
    "not computable": "无法计算",
    "not enough gas data to evaluate": "gas 数据不足，未评估",
    "not living off an old run": "不是靠很久以前的战绩撑着",
    "not measured": "未测",
    "of {0} tokens only {1} cleared 2x while {2} lost money, yet the wallet is up {3} — the profit came from that one token": "{0} 个币里只有 {1} 个翻过 2 倍，{2} 个亏损，却整体盈利 {3} —— 利润几乎只来自那一个币",
    "old hunter": "老猎手",
    "one or two swings, wiped out": "单次或极少次数直接打光",
    "one-shot": "一击必杀",
    "only {0} down more than half": "亏超一半的只有 {0}",
    "only {0} heavy losses": "重亏占比仅 {0}",
    "only {0} of realized gains came from positions netting more than their own cost basis — the rest is round-tripped volume, so the {1} realized P&L cannot be taken at face value": "只有 {0} 的已实现盈利来自净赚超过自身成本的仓位，其余是来回对倒的量 —— 这 {1} 的已实现盈亏不能按面值看",
    "only {0} tokens — no ratio computed on this is meaningful": "样本只有 {0} 个币，任何比率都不成立",
    "operates at a size that does not transfer to you": "规模远超你，行为不可照搬",
    "order channel": "下单渠道",
    "ordinary trading wallet, no distinguishing marks": "普通交易钱包，无特征标记",
    "p25/p50/p75 {0}/{1}/{2} ({3} measurable)": "p25/50/75 {0}/{1}/{2}（{3} 笔）",
    "past that, let it go — its cost is lower than yours, and entering late means buying what it is selling": "超时就别追 —— 它的成本比你低，晚进场等于替它接盘",
    "pre-graduation, you pay up": "它买在你买不到的价位",
    "profit comes from ordering power, not token selection": "收益来自排序权，不是选币",
    "profit concentration not measured (holdings unavailable)": "利润集中度未测（holdings 不可用）",
    "profit concentration {0}": "集中度 {0}",
    "profit concentration {0} (across {1} positions) — one coin carried the record": "利润集中度 {0}（{1} 个仓位口径）—— 一个币扛起了整份战绩，复制不了",
    "profit concentration {0} (largest winner's share of all gains)": "利润集中度 {0}（最大盈利仓位占全部盈利）",
    "profit concentration {0} (only {1} positions — too thin to rely on)": "利润集中度 {0}（仅 {1} 个仓位，样本太薄，未作为判据）",
    "profit from": "利润来自",
    "provenance": "来路",
    "quiet for 24h": "24h 静默",
    "rat trader": "老鼠仓",
    "real volume, and the money went on-chain": "交易量不小，钱流去了链上",
    "record is real": "战绩是真的",
    "renamed repeatedly": "多次改名",
    "retail loser": "亏损散户",
    "rotating": "对冲/换仓",
    "s": " 秒",
    "sample  {0:,} activity rows / {1} tokens · spans {2:.1f}h{3}": "样本  activity {0:,} 条 / {1} 个币 · 覆盖 {2:.1f} 小时{3}",
    "sample too thin": "样本不足",
    "sample too thin — survivability not evaluated": "样本不足，生存性未评估",
    "sandwich bot": "三明治夹子",
    "self-destruct": "自毁装置",
    "sells": "卖出",
    "size": "规模",
    "small cap, heavy slippage": "小市值，滑点大",
    "smart money": "聪明钱",
    "sniper": "狙击",
    "sniper range, no match": "狙击位，拿不到同价",
    "spinning fast, going nowhere": "转得快但原地踏步",
    "spinning top": "陀螺",
    "start at ≤ {0}": "跟单起步 ≤ {0}",
    "start no larger than": "起步别超过",
    "start no larger than {0}": "起步别超过 {0}",
    "steady": "持平",
    "steady hand": "稳步选手",
    "strongly profitable": "强盈",
    "style": "风格",
    "swing": "波段流",
    "swings rarely, earns well — the most copyable rhythm": "出手不多，收益强，节奏可复制",
    "the API's average hold is {0}, but the median first-buy→first-sell in the live sample is {1} — the mean is dragged up by bags it never sold. Read the median, not the mean": "接口均值 {0}，但首买→首卖中位只有 {1} —— 均值被没卖的仓位拖高，看中位",
    "the gain came from picks, not from working the trades": "赢在选得对，不是赢在操作",
    "the most common cell on the board": "最常见的一档",
    "the profit comes from picking right and then sizing up, not from speed — this is the kind you can follow a step behind": "利润来自选对标的然后加到重仓，不是来自手速 —— 这类是可以慢一步跟的",
    "the profit comes from volume of attempts times a few hits, not from picking well. {0}": "利润来自出手次数×少数命中，不是来自选得准。{0}",
    "the profit is volume, and each exit is too thin to survive your slippage and fees": "利润来自成交量，单笔太薄，你的滑点和手续费会直接吃掉它",
    "the track record is genuine, not manufactured": "战绩是真的，不是刷出来的",
    "the {0} you asked about is within that": "你问的 {0} 在这个范围内",
    "the {0} you asked about is {1:.1f}x its own clip of {2} — at that size your fills are worse than the ones this record was built on": "你问的 {0} 是它单笔 {2} 的 {1:.1f} 倍 —— 这个规模下你的成交价会比撑起这份战绩的那些差",
    "thin margins, huge volume": "薄利多销，单笔小、总量大",
    "toe in the water": "试水亏损",
    "token": "代币",
    "token creator": "发币方",
    "tokens": "币数",
    "too small a sample to mean much": "样本太少，标签仅供参考",
    "top 3 winners = {0}": "前 3 个赢家占 {0}",
    "top risk": "最大风险",
    "trades through GMGN — no risk meaning": "通过 GMGN 下单，无风险含义",
    "trades tokens it launched itself": "自己发币自己交易",
    "tried a few times, none worked": "试了几次，没成",
    "typically front-runs launches it is close to": "常见于提前埋伏自己人的盘",
    "unknown": "未知",
    "unrecognised tag, shown verbatim, not used in any gate": "未知标签，原样显示，未参与判定",
    "usually enters around {0}": "大多在市值 {0} 附近进场",
    "value": "数值",
    "value ": "市值",
    "wash trader": "刷量/对敲交易者",
    "whale": "巨鲸",
    "what it is": "定性",
    "whatever it earns, fees and slippage take back": "交易赚的被手续费和滑点磨平",
    "where the profit came from cannot be checked (holdings unavailable) — the {0} in this window is neither confirmed nor refuted. Configure GMGN_PRIVATE_KEY and re-run": "盈利来源无法核验（持仓数据取不到）—— 本窗口这 {0} 既没被证实也没被排除。配置 GMGN_PRIVATE_KEY 后重跑",
    "win rate": "胜率",
    "win {0}": "胜率 {0}",
    "wiped out": "一把归零",
    "worn down": "磨损户",
    "you can keep up": "你跟得上",
    "your normal size": "你自己的常规仓位",
    "zen winner": "佛系赢家",
    "{0:,.0f} trades a day": "每天 {0:,.0f} 笔",
    "{0:,.0f} trades/day": "{0:,.0f} 笔/日",
    "{0:,.0f} trades/day at {1} a clip, and the top 3 winners carry {2} of the profit": "{0:,.0f} 笔/日、单笔均买 {1} 大量试错，前 3 个赢家扛起 {2} 的利润",
    "{0:,.0f} trades/day is not fast; {1} of gains came from positions netting more than their own cost, top 3 winners = {2}": "{0:,.0f} 笔/日不算快，{1} 的利润来自净赚超过自身成本的重仓，前 3 个赢家占 {2}",
    "{0:,.0f} trades/day with profit spread thin (top 3 = {1}), median {2} net per winning exit": "{0:,.0f} 笔/日，利润摊在很多仓位上（前 3 个只占 {1}），单笔中位净赚 {2}",
    "{0:,.0f} trades/day — bot cadence, no hand can keep pace": "{0:,.0f} 笔/日 —— 机器节奏，人手跟不动",
    "{0:,.0f} trades/day, gains neither concentrated (top 3 = {1}) nor speed-driven, median {2} per winning exit": "{0:,.0f} 笔/日，利润既不集中（前 3 个 {1}）也不靠手速，单笔中位净赚 {2}",
    "{0:,.0f}/day": "{0:,.0f}/日",
    "{0:,.1f} {1} on hand": "钱包里还有 {0:,.1f} {1}",
    "{0:,} followers": "{0:,} 粉丝",
    "{0:,} trades ({1:,} buy / {2:,} sell) = {3:,.0f}/day": "{0:,} 笔 · {1:,}买/{2:,}卖 · {3:,.0f}/日",
    "{0:.0f}-day-old wallet": "{0:.0f} 天",
    "{0} (refuted)": "{0}（核验不成立）",
    "{0} **{1}** · 24h bought {2} / sold {3}": "{0} **{1}** · 24h 买 {2} / 卖 {3}",
    "{0} from size positions": "重仓贡献 {0}",
    "{0} hit rate": "胜率 {0}",
    "{0} honeypots in its live book, {1} unsellable — its own screening fails too": "持仓里 {0} 个蜜罐，{1} 卖不出来 —— 它自己也会踩雷",
    "{0} live positions are honeypots ({1}, {2} that cannot be sold) — its own screening did not catch them, and copying it walks into the same ones": "当前持仓里 {0} 个是蜜罐（{1}，合计 {2} 卖不出来）—— 它自己的风控就没挡住，你照抄会踩同样的坑",
    "{0} net per exit · {1} avg gas": "净赚 {0}/笔 · gas {1}",
    "{0} net vs {1} gas": "单笔净赚 {0} vs gas {1}",
    "{0} not measured — the card has no way to show an unmeasured check": "{0} 未测出 —— 决策卡没有地方放「未评估」这个状态",
    "{0} of its buy": "{0}以内",
    "{0} of its tokens are down >50% ({1:,}/{2:,}) — it does not cut": "{0} 的币亏超 50%（{1:,}/{2:,}）—— 不砍仓",
    "{0} of realized gains came from size positions like {1} that netted more than their own cost basis — the profit is priced in, not churned": "{0} 的已实现盈利来自 {1} 这类净赚超过自身成本的重仓 —— 利润来自持仓本身，不是来自换手",
    "{0} of tokens down >50% — it does not cut": "{0} 的币亏超 50% —— 它不砍仓",
    "{0} on {1} cost = {2}": "{0} / 成本 {1} = {2}",
    "{0} over 7 days": "7 天 {0}",
    "{0} over {1} tokens · {2} heavy losses": "{0} 于 {1} 币 · 重亏 {2}",
    "{0} per buy": "{0}/笔",
    "{0} positions down 90%+ with zero sells — riding to zero is the habit": "{0} 个仓位亏 90%+ 且一次没卖 —— 抱到归零是常态",
    "{0} positions · {1} total": "持仓 {0} 个 · 合计 {1}",
    "{0} realized": "已实现 {0}",
    "{0} ridden to zero (down 90%+ with zero sells)": "抱到归零 {0} 个（亏 90%+ 零卖出）",
    "{0} tokens, {1} profitable ({2}), {3}": "{0} 币 · {1} 盈利（{2}）· {3}",
    "{0} tokens, {1} profitable, {2}": "{0} 币 · {1} 盈利 · {2}",
    "{0} {1} — about {2:.0f}x its long-run pace": "{0} {1} —— 比长期均速快 {2:.0f} 倍",
    "{0} {1} — about {2:.0f}x its own long-run pace": "{0} {1} —— 比它一直以来的平均水平快 {2:.0f} 倍",
    "{0} {1}: 7d {2} vs all-time {3}": "{0} {1}：7d {2} vs 全期 {3}",
    "{0} · cadence×P&L {1}": "{0} · 频次×盈亏 {1}",
    "{0} · {1} · window 7d (all-time from profits --period all)": "{0} · {1} · 7d 窗口（全期来自 profits all）",
    "{0} — about {1} of {2} tokens have a realized win · {3} heavy losses": "{0}（{2} 币里约 {1} 个已实现盈利）· 重亏 {3}",
    "⚙️ turnover grind": "⚙️ 周转磨利",
    "⚠️ last trade {0} ago — every figure here describes a wallet that has since gone quiet": "⚠️ 最后一笔在 {0}前 —— 上面所有数字描述的是一个此后已经安静下来的钱包",
    "⚠️ read the median": "⚠️ 看中位",
    "⚡ 5-second flipper on {0} of round trips": "⚡ 秒抛 {0} 的回合 5 秒内出",
    "⚡ SPEED READ": "⚡ 速读",
    "⚪ honeypot NOT checked (holdings unavailable) — this pass covers loss-cutting only, not honeypots": "⚪ 蜜罐未检查（holdings 不可用）—— 本项通过仅基于砍仓行为，不含蜜罐",
    "✂️ scales out, {0:.1f} sells/token": "✂️ 分批止盈 {0:.1f} 卖/币",
    "✅ NO RISK FLAGS": "✅ 无风险旗标",
    "✅ WHAT TO DO NEXT": "✅ 下一步",
    "✅ honeypot flag checked on {0} positions, none hit": "✅ 已检查 {0} 个持仓的蜜罐标记，无命中",
    "✅ {0} honeypot flags ({1}) refuted by fill history — the busiest has {2:,} completed sells; transfer-restricted tokenised stocks, not honeypots": "✅ 蜜罐标记 {0} 个命中（{1}）已被成交记录否掉 —— 最多的一个卖出过 {2:,} 次，是转账受限的代币化股票，不是蜜罐",
    "🆕 new wallet, {0:.0f} days old": "🆕 新号 {0:.0f} 天",
    "🌙 fixed hours, {0} of trades inside one 6-hour window": "🌙 固定时段 {0} 挤在 6 小时内",
    "🍯 {0} honeypot positions ({1}) · {2} unsellable": "🍯 蜜罐持仓 {0} 个（{1}）· {2} 卖不出来",
    "🎯 pick-and-size": "🎯 选币重仓",
    "🎯 sniper, median entry {0}": "🎯 狙击 中位 {0}",
    "🎰 lottery profile, {0} hit rate but {1} tokens above 5x": "🎰 彩票型 胜率 {0} 但 {1} 币过 5 倍",
    "🏦 size-position trader, largest holding {0}": "🏦 重仓 最大 {0}",
    "🏭 launcher (marks its own homework)": "🏭 发币方（自导自演）",
    "🐋 whale, {0} per buy": "🐋 巨鲸 单笔均 {0}",
    "👤 WHO IT IS": "👤 它是谁",
    "💣 dumps in one go on {0} of exits": "💣 一把清 {0}",
    "📉 OUTCOME DISTRIBUTION ({0} tokens — counts tokens, not dollars)": "📉 盈亏分布（{0} 个币，计币不计钱）",
    "📊 NUMBERS (the conclusion is on the right)": "📊 原始数字",
    "📦 concentrated bets, top 3 tokens are {0} of buy spend": "📦 集中押注 前3占买入额 {0}",
    "🔄 WHAT IT IS DOING NOW": "🔄 它现在在干嘛",
    "🕸️ spray-and-hit": "🕸️ 撒网命中",
    "🚦 THE FOUR GATES    {0}": "🚦 四道闸门    {0}",
    "🚩 RISK FLAGS ({0})": "🚩 风险旗标（{0}）",
    "🤖 bot-tier {0:,.0f} trades/day": "🤖 机器级 {0:,.0f}/日",
    "🧩 diffuse accumulation": "🧩 分散积累",
    "🧱 ladders its size positions, median {0:,} buys each": "🧱 分批建仓 中位 {0:,} 笔/仓",
    "🧱 scales in, {0:.1f} buys/token": "🧱 分批建仓 {0:.1f} 买/币",
}

LANG_TABLE = {}


def load_lang(code):
    """Populate LANG_TABLE for `code`. Unknown code => English throughout.

    The table used to live in `lang/<code>.json` beside this file, which cost the skill a
    third shipped file and a whole class of bug that only appeared in one language: a
    reworded string silently fell back to English, a shorter key silently overwrote a
    longer one, and an AST scan that could not see strings reaching T() through a variable
    deleted live entries. Inlining it means the table ships with the code that uses it and
    cannot drift from it -- which is also how gmgn-wallet-score and gmgn-kline-pattern do it.
    """
    LANG_TABLE.clear()
    if code == "zh":
        LANG_TABLE.update(ZH)


def joinclause(parts):
    """Join clauses with the locale's clause separator — a full-width comma in Chinese,
    a comma-space in English. Keyed explicitly rather than inferred, for the same reason
    `joinsym` is: probing a translation to guess the locale reads as a coincidence."""
    return LANG_TABLE.get("__clause_separator__", ", ").join(parts)


def joinsym(items):
    """Join a list of symbols with the locale's separator. Keyed explicitly rather than on
    the separator itself, because ", " is too generic to be safe as a table key."""
    return LANG_TABLE.get("__list_separator__", ", ").join(items)


def T(en, *args):
    """Translate an English template and interpolate. `en` is the table key verbatim."""
    tpl = LANG_TABLE.get(en, en)
    if not args:
        return tpl.replace("{{", "{").replace("}}", "}")
    try:
        return tpl.format(*args)
    except (IndexError, KeyError, ValueError):
        # A translation with the wrong placeholders must not take the report down.
        return en.format(*args)


def f(v, default=0.0):
    """Every numeric field in this API arrives as a JSON string. Never compare raw."""
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def i(v, default=0):
    return int(f(v, default))


def _b(v):
    """API booleans arrive as real bools, 0/1, or "true"/"false" strings."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes")
    return False


def pct(x, digits=1):
    return f"{x * 100:.{digits}f}%"


def usd(v):
    v = f(v)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.2f}M"
    if a >= 1_000:
        return f"{sign}${a / 1_000:.1f}K"
    if a >= 10:
        return f"{sign}${a:,.0f}"
    return f"{sign}${a:.2f}"


def mc(v):
    v = f(v)
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:.0f}"


def dur(sec):
    sec = f(sec)
    if sec <= 0:
        return T('unknown')
    if sec < 60:
        return f"{sec:.0f}{T('s')}"
    if sec < 3600:
        return f"{sec / 60:.0f}{T('m')}"
    if sec < 86400:
        return f"{sec / 3600:.1f}{T('h')}"
    return f"{sec / 86400:.1f}{T('d')}"


def med(xs):
    return statistics.median(xs) if xs else 0.0


# Codepoints that occupy two terminal columns, and the ones that occupy none. The naive
# `ord(c) > 0x2E7F` test this replaced was wrong in both directions: it counted a variation
# selector (U+FE0F) as two columns, so `⚙️` measured 3 and every column it appeared in was
# padded short, and it counted the U+2600-27BF emoji (`⚡ ⚪ ✅`) as one, so lines carrying
# them could exceed COL in a real terminal while the width check called them safe.
ZERO_WIDTH = frozenset({0x200B, 0x200C, 0x200D, 0xFE0E, 0xFE0F, 0x20E3})
WIDE_RANGES = (
    (0x1100, 0x115F),      # Hangul Jamo
    (0x2E80, 0x303E),      # CJK radicals, Kangxi, CJK punctuation
    (0x3041, 0x33FF),      # kana, Hangul compat, CJK compat
    (0x3400, 0x4DBF),      # CJK ext A
    (0x4E00, 0x9FFF),      # CJK unified
    (0xA000, 0xA4CF),      # Yi
    (0xAC00, 0xD7A3),      # Hangul syllables
    (0xF900, 0xFAFF),      # CJK compat ideographs
    (0xFE30, 0xFE6F),      # CJK compat forms
    (0xFF00, 0xFF60),      # fullwidth forms
    (0xFFE0, 0xFFE6),      # fullwidth signs
    (0x1F300, 0x1FAFF),    # emoji: pictographs through symbols-and-pictographs-ext-A
    (0x1F000, 0x1F0FF),    # mahjong, dominoes, cards
    (0x1F100, 0x1F2FF),    # enclosed alphanumeric/ideographic supplement
    (0x2B00, 0x2BFF),      # misc symbols and arrows
)
# Emoji-presentation glyphs below U+2E80 that render wide. Enumerated rather than taken as a
# range because U+2600-27BF mixes wide emoji with narrow dingbats (`✓` is one column), and
# U+2500-257F box drawing — the report's own rules and bars — must stay one column.
WIDE_SYMBOLS = frozenset({
    0x231A, 0x231B, 0x23E9, 0x23EA, 0x23EB, 0x23EC, 0x23F0, 0x23F3,
    0x25FD, 0x25FE, 0x2614, 0x2615, 0x2648, 0x2649, 0x264A, 0x264B, 0x264C,
    0x264D, 0x264E, 0x264F, 0x2650, 0x2651, 0x2652, 0x2653, 0x267F, 0x2693,
    0x26A1, 0x26AA, 0x26AB, 0x26BD, 0x26BE, 0x26C4, 0x26C5, 0x26CE, 0x26D4,
    0x26EA, 0x26F2, 0x26F3, 0x26F5, 0x26FA, 0x26FD, 0x2705, 0x270A, 0x270B,
    0x2728, 0x274C, 0x274E, 0x2753, 0x2754, 0x2755, 0x2757, 0x2795, 0x2796,
    0x2797, 0x27B0, 0x27BF, 0x2B1B, 0x2B1C, 0x2B50, 0x2B55,
})


def cwidth(cp):
    """Terminal columns for one codepoint: 0, 1 or 2."""
    if cp in ZERO_WIDTH or 0x0300 <= cp <= 0x036F:
        return 0
    if cp in WIDE_SYMBOLS:
        return 2
    for lo, hi in WIDE_RANGES:
        if lo <= cp <= hi:
            return 2
    return 1


NATIVE = {"sol": "SOL", "bsc": "BNB", "eth": "ETH", "base": "ETH", "arc": "ARC"}


def usd_exact(v):
    """Whole dollars with separators — no K/M abbreviation.

    The card's headline exists because "$1,000 -> $1,621" needs no conversion to land.
    Run it through usd() and it becomes "$1.0K -> $1.6K", which is both a rounding of the
    thing being demonstrated and a return to the abstraction the card was built to avoid.
    """
    return f"${v:,.0f}"


def quantile(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[k]


def safe_div(a, b, default=0.0):
    return a / b if b else default


# ─── GMGN wallet tags ────────────────────────────────────────────
# `common.tags` is third-party data. Known tags get a meaning and a severity; anything
# unrecognised is printed verbatim and treated as neutral — never silently dropped, and
# never allowed to change control flow.
#   veto_g1 — the P&L itself cannot be trusted
#   veto_g3 — you structurally cannot capture this wallet's edge
#   warn    — changes how you read the numbers
#   good    — a positive signal, still not a reason to skip a gate
TAGS = {
    'wash_trader': ('🚩', 'veto_g1', 'wash trader',
     'P&L may be self-dealt, not market-earned'),
    'sandwich_bot': ('🥪', 'veto_g3', 'sandwich bot',
     'its profit comes from sandwiching orders like yours'),
    'mev_bot': ('🥪', 'veto_g3', 'MEV bot',
     'profit comes from ordering power, not token selection'),
    'rat_trader': ('🐀', 'warn', 'rat trader',
     'typically front-runs launches it is close to'),
    'bundler': ('📦', 'warn', 'bundler',
     'builds its position in the launch block'),
    'sniper': ('🎯', 'warn', 'sniper',
     'enters far too early for you to match its price'),
    'insider': ('🕵️', 'warn', 'insider',
     'an information edge you cannot replicate'),
    'dev': ('🏭', 'warn', 'token creator',
     'trades tokens it launched itself'),
    'kol': ('📣', 'warn', 'KOL',
     'a caller — you are probably not the first one in'),
    'top_followed': ('👥', 'warn', 'heavily followed',
     'copy flow already moved the price; your slippage is worse'),
    'top_renamed': ('🎭', 'warn', 'renamed repeatedly',
     'identity keeps churning; past reputation does not carry'),
    'fresh_wallet': ('🆕', 'warn', 'fresh wallet',
     'no history to check'),
    'smart_money': ('⭐', 'good', 'smart money',
     "GMGN's own positive marker"),
    'bluechip_owner': ('💎', 'good', 'bluechip holder',
     'has held assets that survived'),
    'whale': ('🐋', 'neutral', 'whale',
     'operates at a size that does not transfer to you'),
    'gmgn': ('🔧', 'neutral', 'GMGN user',
     'trades through GMGN — no risk meaning'),
    'photon': ('🔧', 'neutral', 'Photon user',
     'order channel'),
    'bullx': ('🔧', 'neutral', 'BullX user',
     'order channel'),
    'maestro': ('🔧', 'neutral', 'Maestro bot user',
     'order channel'),
    'pepeboost': ('🔧', 'neutral', 'PepeBoost user',
     'order channel'),
}


def read_tags(raw_tags):
    """Return [{key, emoji, sev, name, meaning, known}] — unknown tags kept verbatim."""
    out = []
    for t in raw_tags or []:
        key = str(t).strip()
        row = TAGS.get(key.lower())
        if row:
            emoji, sev, name, meaning = row
            out.append({"key": key, "emoji": emoji, "sev": sev,
                        "name": T(name), "meaning": T(meaning), "known": True})
        else:
            out.append({"key": key, "emoji": "❔", "sev": "neutral",
                        "name": f"`{key}`",
                        "meaning": T('unrecognised tag, shown verbatim, not used in any gate'),
                        "known": False})
    return out


# ─────────────────────────── collection ───────────────────────────


class Gap(Exception):
    pass


def cli(args, timeout=45):
    r = subprocess.run(
        ["gmgn-cli"] + args + ["--raw"], capture_output=True, text=True, timeout=timeout
    )
    if r.returncode != 0:
        raise Gap((r.stderr or r.stdout or "gmgn-cli failed").strip()[:400])
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise Gap("non-JSON response from gmgn-cli")


def unwrap(resp):
    if isinstance(resp, dict) and "data" in resp:
        return resp["data"]
    return resp


def first_row(resp):
    """stats / profits come back as an object, a list, or {list:[...]}, depending on route."""
    d = unwrap(resp)
    if isinstance(d, dict) and isinstance(d.get("list"), list):
        return d["list"][0] if d["list"] else {}
    if isinstance(d, list):
        return d[0] if d else {}
    return d if isinstance(d, dict) else {}


def collect(chain, wallet, gaps):
    """Tiered pull, ordered by how much each call decides.

    One full dossier costs weight 26-28 against a rate-limit bucket of 20, so on a
    cold-ish bucket SOMETHING is refused — the only question is what. The old order spent
    its budget on the two curve-shape windows first and issued `holdings` last, at
    cumulative weight 26, which made the single most decisive call the guaranteed
    casualty: without it G1 cannot corroborate a `wash_trader` tag (the verdict falls to
    HOLD OFF), G4's honeypot half never runs, and the profit engine is dropped. Observed
    live five runs in a row. Meanwhile `stats_30d` and `profits_1d` only add depth to
    readings that already exist.

    So the gate-critical set goes first and fits inside one bucket:

      stats_7d(3) -> profits_all(3) -> holdings(5) = 11   <- verdict decidable here
      activity(3 x 3 = 9)                          = 20   <- copy window, entry band
      stats_30d(3), profits_1d(3)                  = 26   <- depth only, best-effort
      created-tokens(2), conditional

    Nothing about WHAT is asked changed — same routes, parameters and page count. Only the
    sequence moved, so no threshold, formula or verdict row is affected.
    """
    d = {}

    # ── Tier 1: the verdict cannot be issued without these. Weight 11, inside one bucket.
    d["stats_7d"] = first_row(
        cli(["portfolio", "stats", "--chain", chain, "--wallet", wallet, "--period", "7d"])
    )

    # profits_all is a G2 input: losing it makes G2 unevaluable, so it outranks the two
    # windows that only add depth.
    try:
        d["profits_all"] = first_row(
            cli(["portfolio", "profits", "--chain", chain, "--wallet", wallet, "--period", "all"])
        )
    except Gap as e:
        d["profits_all"] = {}
        gaps.append(f"profits_all: {e}")


    # holdings is CRITICAL auth (needs GMGN_PRIVATE_KEY). Absent key is the normal case.
    # `--sell-out` is documented but rejected by gmgn-cli 1.5.8 ("unknown option"), so it
    # is not passed. The response array is `list`; `holdings` is kept only as a fallback in
    # case a future version renames it to match the docs.
    try:
        raw_h = unwrap(cli(["portfolio", "holdings", "--chain", chain, "--wallet", wallet,
                            "--limit", "50", "--order-by", "total_profit", "--direction", "desc"]))
        d["holdings"] = raw_h.get("list") or raw_h.get("holdings") or []
        if not d["holdings"]:
            gaps.append(T('holdings came back empty — live book, profit concentration and the honeypot check were all skipped'))
    except Gap as e:
        d["holdings"] = []
        # Attribute the failure to its actual cause. This branch used to hardcode the
        # missing-credential wording for every failure, so a rate-limit refusal told the
        # reader to go and configure a key they had already configured — the wrong
        # instruction, and it hid the real reason. Anything that is not recognisably a
        # limiter refusal is reported verbatim rather than guessed at.
        txt = str(e)
        if "429" in txt or "RATE_LIMIT" in txt:
            gaps.append(
                T('holdings refused by the rate limiter (not an auth problem): {0} — profit concentration falls back to bucket inference; live book and honeypot check missing. Re-run once the limit resets.', e)
            )
        elif "SIGNATURE_INVALID" in txt or "signature invalid" in txt.lower():
            gaps.append(
                T('holdings refused: the private key IS configured, but its signature was '
                  'rejected: {0} — check GMGN_PRIVATE_KEY holds the full PEM (BEGIN/END lines '
                  'included, no stray whitespace) and that it is the key paired with this '
                  'GMGN_API_KEY. Adding the variable again will not help. Profit '
                  'concentration falls back to bucket inference; live book and honeypot '
                  'check missing', e)
            )
        elif "PRIVATE_KEY" in txt or "401" in txt or "403" in txt:
            gaps.append(
                T('holdings unavailable (needs GMGN_PRIVATE_KEY / critical auth): {0} — profit concentration falls back to bucket inference; live book and honeypot check missing', e)
            )
        else:
            gaps.append(
                T('holdings failed: {0} — profit concentration falls back to bucket inference; live book and honeypot check missing', e)
            )

    # ── Tier 2: behaviour. activity is the only source of the copy window and the entry
    # band, and the page count stays at 3 — trimming it would move G3's entry p50 and
    # starve the sample gates, which changes what is measured, not how fast.
    acts, cursor = [], None
    for _page in range(3):
        args = ["portfolio", "activity", "--chain", chain, "--wallet", wallet, "--limit", "100"]
        if cursor:
            args += ["--cursor", str(cursor)]
        try:
            raw = unwrap(cli(args))
        except Gap as e:
            gaps.append(f"activity: {e}")
            break
        page = raw.get("activities") or []
        acts += page
        cursor = raw.get("next")
        if not page or not cursor:
            break
    d["activity"] = acts
    if not acts:
        gaps.append(
            T('activity empty — copy window, entry band and scale-in/out shape were not evaluated')
        )

    # ── Tier 3: depth only. Both windows enrich readings that already exist above, so
    # they are the correct things to lose when the bucket runs dry.
    for key, args in (
        ("stats_30d", ["portfolio", "stats", "--period", "30d"]),
        ("profits_1d", ["portfolio", "profits", "--period", "1d"]),
    ):
        try:
            d[key] = first_row(cli(args[:2] + ["--chain", chain, "--wallet", wallet] + args[2:]))
        except Gap as e:
            d[key] = {}
            gaps.append(f"{key}: {e}")

    # ── Tier 4 — only when the wallet looks like a launcher.
    common = d["stats_7d"].get("common") or {}
    pnl = d["stats_7d"].get("pnl_stat") or {}
    created = i(common.get("created_token_count"))
    if created > 0 and created > 0.5 * max(1, i(pnl.get("token_num"))):
        try:
            d["created_tokens"] = unwrap(
                cli(["portfolio", "created-tokens", "--chain", chain, "--wallet", wallet])
            )
        except Gap as e:
            d["created_tokens"] = {}
            gaps.append(f"created-tokens: {e}")
    return d


# ─────────────────────────── metrics ───────────────────────────


def ev_type(a):
    return str(a.get("event_type") or a.get("type") or "").lower()


def tok_addr(a):
    t = a.get("token") or {}
    return t.get("address") or t.get("token_address")


def h_get(row, *names):
    """First present field among `names` — the holdings schema differs from the docs."""
    for nm in names:
        if row.get(nm) is not None:
            return row[nm]
    return None


def window_roi(row, cost_key, profit_key):
    """ROI for a window = realized profit / the cost that produced it."""
    cost = f(row.get(cost_key))
    prof = f(row.get(profit_key))
    if cost <= 0:
        return None
    return prof / cost


def compute(d, latency_s, my_size):
    m = {}
    s7 = d.get("stats_7d") or {}
    s30 = d.get("stats_30d") or {}
    p1 = d.get("profits_1d") or {}
    pall = d.get("profits_all") or {}
    pnl = s7.get("pnl_stat") or {}
    common = s7.get("common") or {}

    m["buy"] = i(s7.get("buy", s7.get("buy_count")))
    m["sell"] = i(s7.get("sell", s7.get("sell_count")))
    m["trades"] = m["buy"] + m["sell"]
    m["per_day"] = m["trades"] / 7.0
    m["token_num"] = i(pnl.get("token_num"))
    m["winrate"] = f(pnl.get("winrate"))
    m["avg_hold_s"] = f(pnl.get("avg_holding_period"))
    m["realized_7d"] = f(s7.get("realized_profit"))
    m["cost_7d"] = f(s7.get("bought_cost", s7.get("total_cost")))
    m["avg_buy_usd"] = safe_div(m["cost_7d"], m["buy"])
    m["buckets"] = {
        "gt5": i(pnl.get("pnl_gt_5x_num")),
        "x2_5": i(pnl.get("pnl_2x_5x_num")),
        "x0_2": i(pnl.get("pnl_0x_2x_num")),
        "n50_0": i(pnl.get("pnl_nd5_0x_num")),
        "lt_n50": i(pnl.get("pnl_lt_nd5_num")),
    }
    m["lt50_share"] = safe_div(m["buckets"]["lt_n50"], max(1, m["token_num"]))
    # The 0-200% bucket and the win rate disagree, and the report used to print both without
    # saying so. A live wallet showed 188 of 209 tokens in that bucket next to a 23.9% win
    # rate: 188 would imply 90%. Only one reading satisfies both numbers — the band absorbs
    # every token with no realized result yet (bought, not yet sold => realized ROI 0, which
    # sits on that band's lower edge), so its size is not a count of wins. `unsettled` is
    # that difference, and it is stated rather than left for the reader to notice.
    m["implied_winners"] = round(m["winrate"] * m["token_num"])
    m["unsettled"] = max(0, m["buckets"]["x0_2"] - m["implied_winners"])
    m["dist_gap"] = (
        m["token_num"] >= 20
        and m["buckets"]["x0_2"] > 0
        and m["unsettled"] >= 0.25 * m["buckets"]["x0_2"]
    )
    m["winners"] = m["buckets"]["gt5"] + m["buckets"]["x2_5"] + m["buckets"]["x0_2"]

    # identity
    m["tags"] = common.get("tags") or ([common["tag"]] if common.get("tag") else [])
    m["tag_info"] = read_tags(m["tags"])
    m["tag_sev"] = {t["sev"] for t in m["tag_info"]}
    m["twitter"] = common.get("twitter_username") or ""
    m["twitter_name"] = common.get("twitter_name") or common.get("name") or ""
    m["blue"] = bool(common.get("is_blue_verified"))
    m["followers"] = i(common.get("followers_count"))
    m["created_tokens_n"] = i(common.get("created_token_count"))
    m["created_at"] = i(common.get("created_at"))
    m["age_days"] = (time.time() - m["created_at"]) / 86400 if m["created_at"] else None
    m["fund_from"] = common.get("fund_from") or ""
    m["fund_from_address"] = common.get("fund_from_address") or ""
    m["fund_amount"] = f(common.get("fund_amount"))
    m["follow_count"] = i(common.get("follow_count"))
    m["is_dev"] = m["created_tokens_n"] > 0 and m["created_tokens_n"] > 0.5 * max(1, m["token_num"])

    # form curve — the trap detector: great all-time, dead this week
    def stats_roi(row):
        """`realized_profit_pnl` is a ratio, not a percentage. A zero cost basis means
        the window has no closed trades — that is 'unknown', never 'zero return'."""
        if not row:
            return None
        cost = f(row.get("bought_cost", row.get("total_cost")))
        if cost <= 0:
            return None
        return f(row.get("realized_profit_pnl", row.get("pnl")))

    m["roi_1d"] = window_roi(p1, "realized_profit_cost", "realized_profit")
    m["roi_7d"] = stats_roi(s7)
    m["roi_30d"] = stats_roi(s30)
    m["roi_all"] = window_roi(pall, "total_realized_profit_cost", "total_realized_profit")
    m["realized_all"] = f(pall.get("total_realized_profit")) if pall else None
    m["unrealized"] = f(pall.get("unrealized_profit")) if pall else None
    m["realized_1d"] = f(p1.get("realized_profit")) if p1 else None

    r7, ra = m["roi_7d"], m["roi_all"]
    if r7 is None or ra is None:
        m["form"] = ("⚪", T('cannot tell'))
    elif ra <= 0 and r7 <= 0:
        m["form"] = ("⚫", T('never worked'))
    elif ra > 0.1 and r7 <= -0.1:
        m["form"] = ("💀", T('broken down'))
    elif r7 > max(0.1, ra):
        m["form"] = ("🔥", T('heating up'))
    elif abs(r7 - ra) <= 0.15:
        m["form"] = ("➡️", T('steady'))
    elif r7 < ra - 0.15:
        m["form"] = ("❄️", T('cooling off'))
    else:
        m["form"] = ("➡️", T('steady'))

    # ── activity-derived behaviour ──
    acts = d.get("activity") or []
    trade_rows = [a for a in acts if ev_type(a) in ("buy", "sell")]
    m["sampled"] = len(trade_rows)
    ts = [f(a.get("timestamp")) for a in trade_rows if f(a.get("timestamp")) > 0]
    m["span_h"] = (max(ts) - min(ts)) / 3600 if len(ts) >= 2 else 0.0
    # The report's window is 7 days. A sample that reaches beyond it is describing a season
    # while sitting next to 7d figures, and the reader cannot see that from the numbers.
    # (72h was the first cut and was wrong: it flagged on-window samples, printing
    # "measured across 7 days, not just this week" -- a contradiction.)
    m["span_stale"] = m["span_h"] > 24 * 8
    m["hit_limit"] = len(acts) >= 300

    mcaps, gas, buy_costs = [], [], []
    by_tok = {}
    for a in trade_rows:
        et = ev_type(a)
        addr = tok_addr(a)
        if addr:
            by_tok.setdefault(addr, []).append(a)
        if f(a.get("gas_usd")) > 0:
            gas.append(f(a.get("gas_usd")))
        if et == "buy":
            sup = f((a.get("token") or {}).get("total_supply"))
            px = f(a.get("price_usd"))
            if sup > 0 and px > 0:
                mcaps.append(px * sup)
            if f(a.get("cost_usd")) > 0:
                buy_costs.append(f(a.get("cost_usd")))
    m["avg_gas_usd"] = safe_div(sum(gas), len(gas)) if len(gas) >= 10 else 0.0
    m["median_buy_usd"] = med(buy_costs)
    # gas as a share of trade size — the number that says whether the edge survives friction
    denom = m["median_buy_usd"] or m["avg_buy_usd"]
    m["gas_share"] = (m["avg_gas_usd"] / denom) if (gas and denom > 0) else None
    m["entry_p25"] = quantile(mcaps, 0.25)
    m["entry_p50"] = quantile(mcaps, 0.50)
    m["entry_p75"] = quantile(mcaps, 0.75)
    m["entry_n"] = len(mcaps)
    m["entry_sub100k"] = safe_div(sum(1 for x in mcaps if x < 100_000), len(mcaps))
    m["entry_n_thin"] = len(mcaps) < 8

    copy_windows, accum_windows, buys_per_tok, sells_per_tok, flip5 = [], [], [], [], 0
    round_trips = 0
    dump_shape = 0
    for addr, evs in by_tok.items():
        evs = sorted(evs, key=lambda e: f(e.get("timestamp")))
        buys = [e for e in evs if ev_type(e) == "buy"]
        sells = [e for e in evs if ev_type(e) == "sell"]
        buys_per_tok.append(len(buys))
        sells_per_tok.append(len(sells))
        if buys and sells:
            t_first_buy = f(buys[0].get("timestamp"))
            t_first_sell = f(sells[0].get("timestamp"))
            if t_first_sell > t_first_buy:
                copy_windows.append(t_first_sell - t_first_buy)
                round_trips += 1
                if t_first_sell - t_first_buy <= 5:
                    flip5 += 1
        if len(buys) >= 2:
            accum_windows.append(f(buys[-1].get("timestamp")) - f(buys[0].get("timestamp")))
        if sells:
            sold = sum(f(e.get("cost_usd")) for e in sells)
            biggest = max(f(e.get("cost_usd")) for e in sells)
            if sold > 0 and biggest / sold >= 0.8:
                dump_shape += 1
    m["copy_window_s"] = med(copy_windows)
    m["copy_window_n"] = len(copy_windows)
    m["accum_window_s"] = med(accum_windows)
    m["avg_buys_per_token"] = safe_div(sum(buys_per_tok), len(buys_per_tok))
    # ✂️ scales-out needs more than a couple of tokens before "2.0 sells/token" means
    # anything; on one token it is that token, not a habit.
    m["avg_sells_per_token"] = (safe_div(sum(sells_per_tok), len(sells_per_tok))
                                if len(sells_per_tok) >= 5 else 0.0)
    # ⚡ 5-second flipper: with 2 round trips this is 0%, 50% or 100% by arithmetic.
    m["flip5_rate"] = safe_div(flip5, round_trips) if round_trips >= 10 else 0.0
    _sellers = sum(1 for v in sells_per_tok if v)
    m["dump_share"] = safe_div(dump_shape, _sellers) if _sellers >= 10 else 0.0
    m["distinct_tokens_sampled"] = len(by_tok)

    # Concentration of buy spend across tokens, and clustering in the day. Both are
    # activity-derived, so both are meaningless on a short sample: the top 3 of 3 tokens is
    # 100% by arithmetic, and any sample spanning under 12 hours "clusters" inside a 6-hour
    # window by arithmetic too. A live run fired both on a 14-hour sample with no warning.
    buy_by_tok = {}
    for a in trade_rows:
        if ev_type(a) == "buy" and tok_addr(a):
            buy_by_tok[tok_addr(a)] = buy_by_tok.get(tok_addr(a), 0.0) + f(a.get("cost_usd"))
    tot_buy = sum(buy_by_tok.values())
    m["top3_buy_share"] = (
        safe_div(sum(sorted(buy_by_tok.values(), reverse=True)[:3]), tot_buy)
        if tot_buy > 0 and len(buy_by_tok) >= 5 else None
    )
    hours = [0] * 24
    for t in ts:
        hours[int((t // 3600) % 24)] += 1
    if len(ts) >= 20 and m["span_h"] >= 12:
        best = max(sum(hours[(h + k) % 24] for k in range(6)) for h in range(24))
        m["hour_peak_share"] = safe_div(best, len(ts))
    else:
        m["hour_peak_share"] = None

    # last 24h posture — what it is doing RIGHT NOW
    now = max(ts) if ts else time.time()
    b24 = s24 = 0.0
    recent_buys = {}
    for a in trade_rows:
        if now - f(a.get("timestamp")) > 86400:
            continue
        c = f(a.get("cost_usd"))
        if ev_type(a) == "buy":
            b24 += c
            sym = (a.get("token") or {}).get("symbol") or (tok_addr(a) or "?")[:6]
            prev = recent_buys.get(sym, (0.0, 0.0))
            sup = f((a.get("token") or {}).get("total_supply"))
            px = f(a.get("price_usd"))
            recent_buys[sym] = (prev[0] + c, (px * sup) if (sup > 0 and px > 0) else prev[1])
        else:
            s24 += c
    m["buy_usd_24h"], m["sell_usd_24h"] = b24, s24
    m["recent_buys"] = [(k, v[0], v[1]) for k, v in
                        sorted(recent_buys.items(), key=lambda kv: -kv[1][0])[:5]]
    if b24 + s24 <= 0:
        m["posture"] = ("😴", T('quiet for 24h'))
    elif s24 > 2 * b24:
        m["posture"] = ("📤", T('distributing'))
    elif b24 > 2 * s24:
        m["posture"] = ("🧊", T('accumulating'))
    else:
        m["posture"] = ("🔁", T('rotating'))

    # ── holdings-derived: profit concentration + hold-to-zero ──
    h = d.get("holdings") or []
    m["holdings_n"] = len(h)
    m["pcr"] = None
    m["pcr_source"] = None
    m["pcr_trusted"] = False
    m["pcr_represents_record"] = False
    m["one_coin_note"] = None
    if h:
        profits = sorted((f(x.get("total_profit")) for x in h), reverse=True)  # confirmed name
        pos = [p for p in profits if p > 0]
        if pos:
            m["pcr"] = safe_div(pos[0], sum(pos))
            m["pcr_source"] = "holdings"
            # A concentration ratio over 2 winners is arithmetic, not evidence. Requiring
            # 3+ winners and 8+ positions is what stops this vetoing every small sample:
            # with one winner in the page, PCR is 100% by definition.
            m["pcr_trusted"] = len(pos) >= 3 and len(h) >= 8
            # ...and the open book has to be most of what it ever traded before its
            # concentration may speak for the record.
            m["pcr_represents_record"] = (
                m["pcr_trusted"] and len(h) >= 0.5 * max(1, m["token_num"])
            )
        m["hold_to_zero"] = sum(
            1
            for x in h
            if f(h_get(x, "total_profit_pnl", "profit_change")) <= -0.9
            and i(h_get(x, "history_total_sells", "sell_tx_count")) == 0
        )
        m["open_book"] = [
            {
                "sym": (x.get("token") or {}).get("symbol") or "?",
                "usd": f(x.get("usd_value")),
                "chg": f(h_get(x, "total_profit_pnl", "profit_change")),
                "cost": f(h_get(x, "accu_cost", "cost", "history_bought_cost")),
                "sells": i(h_get(x, "history_total_sells", "sell_tx_count")),
            }
            for x in sorted(h, key=lambda x: -f(x.get("usd_value")))[:5]
            if f(x.get("usd_value")) > 0
        ]
        m["open_value"] = sum(f(x.get("usd_value")) for x in h)
    else:
        m["hold_to_zero"] = None
        m["open_book"] = []
        m["open_value"] = None

    # One-coin detector, independent of holdings. This is a *count* fact from the P&L
    # buckets — never a synthesised percentage. A wallet that is net positive on the
    # strength of at most one >200% token, with a losing majority, was carried by that token.
    big = m["buckets"]["gt5"] + m["buckets"]["x2_5"]
    losers = m["buckets"]["n50_0"] + m["buckets"]["lt_n50"]
    if (
        m["realized_7d"] > 0
        and big <= 1
        and m["token_num"] >= 8
        and losers > 0.5 * m["token_num"]
    ):
        m["one_coin_note"] = T('of {0} tokens only {1} cleared 2x while {2} lost money, yet the wallet is up {3} — the profit came from that one token', m['token_num'], big, losers, usd(m['realized_7d']))

    # ── position scale, from holdings ────────────────────────────────────────────
    # `avg_buy_usd` measures the CLIP, not the POSITION. A wallet that ladders a $54K
    # position together out of $3.4K clips reads as a $3.4K trader on clip size alone, and
    # a live run duly labelled exactly that wallet "ordinary, no distinguishing marks".
    # Position size and buys-per-position are the honest markers, and holdings carries
    # both — `history_total_buys` is the wallet's whole history on that token, not the
    # 300-row activity slice.
    m["top_pos_usd"] = None
    m["med_buys_per_pos"] = None
    if h:
        vals = sorted((f(x.get("usd_value")) for x in h), reverse=True)
        if vals and vals[0] > 0:
            m["top_pos_usd"] = vals[0]
        # Median over the WHOLE book is dominated by one-and-done dust positions, which
        # says nothing about how the wallet builds the positions it cares about. Take the
        # five largest by value — laddering is a property of size positions.
        top = sorted(h, key=lambda x: -f(x.get("usd_value")))[:5]
        bpp = sorted(b for b in (i(h_get(x, "history_total_buys", "buy_tx_count")) for x in top) if b > 0)
        if len(bpp) >= 3:
            m["med_buys_per_pos"] = bpp[len(bpp) // 2]

    # ── wash-trade corroboration ────────────────────────────────────────────────
    # `wash_trader` is a third-party heuristic label, not a finding. On this dataset it
    # fires on any wallet that round-trips a low-liquidity token many times — including a
    # $1K sliver of tokenised-stock churn on a wallet whose actual P&L is six-figure
    # memecoin positions. Obeying the tag alone mis-classified exactly that wallet as
    # un-copyable. So the tag now has to be corroborated against behaviour before it can
    # veto anything, and the corroboration is a single number.
    #
    # A position carries a GENUINE edge when its realized profit exceeds its own cost
    # basis, or clears $1,000 net per exit. Self-dealing cannot manufacture either: wash
    # volume nets to roughly zero minus fees, so its per-exit figure is small or negative.
    # `conviction_share` is the fraction of all realized gains that came from such
    # positions. High share → the record is NOT explained by round-tripping.
    m["conviction_share"] = None
    m["conviction_top"] = []
    if h:
        gains, conv, conv_syms, gainers = 0.0, 0.0, [], 0
        for x in h:
            # `realized_profit` is the right numerator — a wash trader's closed loops are
            # what the tag is about. Fall back to `total_profit` only when the row omits it.
            rp = f(h_get(x, "realized_profit", "total_profit"))
            if rp <= 0:
                continue
            gains += rp
            gainers += 1
            cost = f(h_get(x, "accu_cost", "cost", "history_bought_cost"))
            sells = i(h_get(x, "history_total_sells", "sell_tx_count"))
            per_exit = safe_div(rp, sells) if sells > 0 else rp
            if (cost > 0 and rp >= cost) or per_exit >= 1000:
                conv += rp
                conv_syms.append(((x.get("token") or {}).get("symbol") or "?", rp))
        if gains > 0:
            if gainers >= 3:
                m["conviction_share"] = conv / gains
            m["conviction_top"] = sorted(conv_syms, key=lambda kv: -kv[1])[:3]

    # ── where the money came from ───────────────────────────────────────────────
    # "It made 15.8%" does not tell a reader whether the edge is speed or selection, and
    # those two are copied in completely different ways: you cannot out-click a 288-trade/day
    # sniper, but you can wait and buy what a conviction wallet just laddered into. So
    # attribute the gains before interpreting them.
    #   gain_top3_share — do a handful of winners carry it, or is it spread thin?
    #   med_gain_per_exit — is each exit worth taking, or is this volume grinding?
    m["gain_top3_share"] = None
    m["med_gain_per_exit"] = None
    if h:
        wins = []
        for x in h:
            rp = f(h_get(x, "realized_profit", "total_profit"))
            if rp <= 0:
                continue
            sells = i(h_get(x, "history_total_sells", "sell_tx_count"))
            wins.append((rp, safe_div(rp, sells) if sells > 0 else rp))
        if wins:
            pe = sorted(w[1] for w in wins)
            m["med_gain_per_exit"] = pe[len(pe) // 2]
            # A top-3 share over 3 or fewer winners is 100% by definition. Same guard as
            # pcr_trusted, and for the same reason: it is arithmetic, not evidence.
            if len(wins) > 3:
                tot = sum(w[0] for w in wins)
                top3 = sum(sorted((w[0] for w in wins), reverse=True)[:3])
                m["gain_top3_share"] = safe_div(top3, tot)

    # If a wash-trading tag is present but the gains demonstrably come from positions with
    # a real net edge, demote the tag in place: it stays visible as a warning with the
    # number that refuted it, and it no longer vetoes G1. Mutating `tag_info` here means
    # every render site downstream follows automatically.
    m["wash_refuted"] = None
    cs = m["conviction_share"]
    if cs is not None and cs >= 0.5:
        for t in m["tag_info"]:
            if t["sev"] == "veto_g1":
                m["wash_refuted"] = {"share": cs, "tag": t["name"]}
                # "hidden" renders nowhere: every display site selects an explicit severity.
                # The tag is not shown at all rather than shown struck through — G1 prints
                # where the profit came from instead, which is the fact behind the decision.
                t["sev"] = "hidden"
                t["refuted"] = True

    # ── dev record ──
    ct = d.get("created_tokens") or {}
    if ct:
        m["dev_open"] = i(ct.get("open_count"))
        m["dev_inner"] = i(ct.get("inner_count"))
        m["dev_total"] = m["dev_open"] + m["dev_inner"]
        m["dev_open_ratio"] = (
            f(ct.get("open_ratio")) if ct.get("open_ratio") is not None
            else safe_div(m["dev_open"], max(1, m["dev_total"]))
        )
        ath = ct.get("creator_ath_info") or {}
        m["dev_ath_mc"] = f(ath.get("ath_mc"))
    else:
        m["dev_total"] = None

    # ── friction: the numbers that decide whether the edge survives being copied ──
    # Per-trade net is the yardstick everything else is measured against. A wallet netting
    # $26 a trade while paying $4 of gas has already given a third of its edge away, and
    # your slippage comes out of what is left.
    # Fields `portfolio stats` returns that nothing read. Each answers a question a reader
    # asks out loud and the report could not previously answer.
    #   native_balance — the dry powder. GMGN's own leaderboard puts it in column two.
    #   last_timestamp — freshness. A wallet last active three days ago is not the same
    #                    wallet as one trading right now, and every other figure here is
    #                    silent about which it is.
    m["native_balance"] = f(s7.get("native_balance"))
    last_ts = f(s7.get("last_timestamp"))
    ref_now = f(d.get("_now")) or time.time()
    m["idle_s"] = max(0.0, ref_now - last_ts) if last_ts > 0 else None
    m["stale"] = m["idle_s"] is not None and m["idle_s"] > 48 * 3600

    m["net_per_sell"] = safe_div(m["realized_7d"], m["sell"]) if m["sell"] >= 5 else 0.0

    # `portfolio stats` reports the fees actually paid in the window — `bought_fee` and
    # `sold_fee` — and this used to ignore both, estimating friction instead from the gas
    # median of a 300-row activity sample times the trade count. On a live wallet the
    # estimate said gas ate 0.0% of the profit while the real fees were $4,408 against
    # $167,237 realized, i.e. 2.6%. Two orders of magnitude, and the exact figure was in a
    # response already in hand. The estimate stays as the fallback for chains or versions
    # that omit the fee fields, and the report says which one it is showing.
    m["fee_total"] = f(s7.get("bought_fee")) + f(s7.get("sold_fee"))
    m["fee_exact"] = m["fee_total"] > 0
    if m["fee_exact"] and m["realized_7d"] > 0:
        m["gas_drag"] = m["fee_total"] / m["realized_7d"]
        m["gas_total_est"] = m["fee_total"]
    elif m["avg_gas_usd"] > 0 and m["trades"] > 0 and m["realized_7d"] > 0:
        m["gas_total_est"] = m["avg_gas_usd"] * m["trades"]
        m["gas_drag"] = m["gas_total_est"] / m["realized_7d"]
    else:
        m["gas_total_est"] = None
        m["gas_drag"] = None

    # Reconcile the average against the median. `avg_holding_period` counts every position
    # including bags never sold, so a scalper can report a 4-day "average hold". Reporting
    # both without saying which is which is exactly the reasoning burden to remove.
    m["hold_conflict"] = None
    if m["avg_hold_s"] > 0 and m["copy_window_n"] >= 3 and m["copy_window_s"] > 0:
        if m["avg_hold_s"] > 8 * m["copy_window_s"]:
            m["hold_conflict"] = T("the API's average hold is {0}, but the median first-buy→first-sell in the live sample is {1} — the mean is dragged up by bags it never sold. Read the median, not the mean", dur(m['avg_hold_s']), dur(m['copy_window_s']))

    # ── honeypots in the live book ──
    # `token.is_honeypot` ships inline on every holdings row, so this costs nothing and is
    # available whenever holdings is. `security_checked` records how many rows actually
    # carried the flag, so a missing flag is never read as "clean".
    hp_names, flagged, hp_refuted = [], 0, []
    for h_row in (d.get("holdings") or []):
        tk = h_row.get("token") or {}
        if tk.get("is_honeypot") is None:
            continue
        flagged += 1
        if not _b(tk.get("is_honeypot")):
            continue
        sym = tk.get("symbol") or (tok_addr(h_row) or "?")[:6]
        sells = i(h_get(h_row, "history_total_sells", "sell_tx_count"))
        # A honeypot is a token you CANNOT sell. When the same row records completed sells,
        # the flag is contradicted by this wallet's own history — the usual cause is a
        # transfer-restricted RWA / tokenised-stock contract that trips naive sell
        # simulators. A live run failed G4 on seven such "honeypots", one of which this
        # wallet had sold 101 times. The refutation is free: it is on the same row.
        if sells > 0:
            hp_refuted.append({"sym": sym, "sells": sells})
            continue
        hp_names.append({"sym": sym, "usd": f(h_row.get("usd_value"))})
    m["honeypots"] = hp_names
    m["honeypot_usd"] = sum(x["usd"] for x in hp_names)
    m["hp_refuted"] = hp_refuted
    m["security_checked"] = flagged

    # Where it hunts — launchpad mix across the live book, also inline on token.
    lp = {}
    for h_row in (d.get("holdings") or []):
        name = ((h_row.get("token") or {}).get("launchpad_platform")
                or (h_row.get("token") or {}).get("launchpad"))
        if name:
            lp[str(name)] = lp.get(str(name), 0) + 1
    m["launchpads"] = sorted(lp.items(), key=lambda kv: -kv[1])[:3]

    # ── the decision card's numbers ──────────────────────────────────────────────
    # "+62.1%" is a ratio a reader has to convert before it means anything. The same fact
    # told as money needs no conversion: $1,000 -> $1,621. Nothing new is fetched; this is
    # roi_7d wearing clothes a newcomer already owns.
    m["story_stake"] = 1000.0
    m["story_out"] = (1000.0 * (1.0 + m["roi_7d"])) if m["roi_7d"] is not None else None
    # How much hotter than its own baseline. Only meaningful when the baseline is positive:
    # against a negative or ~zero all-time ROI the ratio is noise, so it is dropped rather
    # than printed as a huge multiple that means nothing.
    m["pace_x"] = None
    if m["roi_7d"] is not None and m["roi_all"] is not None and m["roi_all"] >= 0.02:
        r = m["roi_7d"] / m["roi_all"]
        if r >= 1.5:
            m["pace_x"] = r

    # size guidance
    # The size the reader intends, checked against the wallet's own clip. Above the wallet's
    # own size your slippage is worse than its, so its results stop describing you — which
    # is the whole reason size_cap exists. Stating the multiple makes that concrete.
    m["my_size"] = my_size
    m["size_ratio"] = (my_size / m["avg_buy_usd"]) if (my_size and m["avg_buy_usd"] > 0) else None
    m["size_cap"] = m["avg_buy_usd"] * 0.5 if m["avg_buy_usd"] > 0 else None
    m["latency_s"] = latency_s
    return m


# ─────────────────────────── the four gates ───────────────────────────


def gates(m):
    """Each gate: (pass?, one-line reason with the number that decided it)."""
    g = {}

    # No trades at all: nothing is assessable. Every gate is ⚪, not ❌ — "unevaluated"
    # and "failed" must never render the same, or a fresh wallet reads as a bad wallet.
    if m["trades"] == 0:
        blank = T('no buys or sells in 7 days — nothing to evaluate')
        return {k: (None, blank) for k in ("G1", "G2", "G3", "G4")}

    # G1 AUTHENTICITY — a wash-trading marker outranks every other test here. If the
    # volume may be self-dealt, the win rate, the ROI and the bucket distribution are all
    # measuring the wallet trading against itself, and no amount of good-looking
    # distribution rescues that.
    wash = [t for t in m["tag_info"] if t["sev"] == "veto_g1"]
    if wash and m["conviction_share"] is None:
        # Tag present and uncheckable. This is exactly the ⚪ case: "we could not verify" is
        # not "confirmed fake", and it is not "fine" either. Do not manufacture a ❌.
        g["G1"] = (
            None,
            T('where the profit came from cannot be checked (holdings unavailable) — the {0} in this window is neither confirmed nor refuted. Configure GMGN_PRIVATE_KEY and re-run', usd(m['realized_7d'])),
        )
    elif wash:
        g["G1"] = (
            False,
            T('only {0} of realized gains came from positions netting more than their own cost basis — the rest is round-tripped volume, so the {1} realized P&L cannot be taken at face value', pct(m['conviction_share']), usd(m['realized_7d'])),
        )
    elif m["is_dev"]:
        g["G1"] = (
            False,
            T('launcher wallet: created {0} vs traded {1} — its win rate and entry timing are self-authored, not a market read', m['created_tokens_n'], m['token_num']),
        )
    elif m["token_num"] < 5:
        g["G1"] = (
            False,
            T('only {0} tokens — no ratio computed on this is meaningful', m['token_num']),
        )
    elif m["one_coin_note"]:
        g["G1"] = (False, m["one_coin_note"])
    elif m["pcr_represents_record"] and m["pcr"] >= 0.75:
        g["G1"] = (
            False,
            T('profit concentration {0} (across {1} positions) — one coin carried the record', pct(m['pcr']), m['holdings_n']),
        )
    else:
        if m["pcr_represents_record"]:
            pcr_txt = T('profit concentration {0}', pct(m['pcr']))
        elif m["pcr_trusted"]:
            pcr_txt = T('current book is {0} concentrated ({1} open of {2:,} traded, so this '
                        'says nothing about the closed record)',
                        pct(m['pcr']), m['holdings_n'], m['token_num'])
        elif m["pcr"] is not None:
            pcr_txt = T('profit concentration {0} (only {1} positions — too thin to rely on)', pct(m['pcr']), m['holdings_n'])
        elif m["holdings_n"]:
            pcr_txt = T('no open position is in profit, so concentration says nothing here')
        else:
            pcr_txt = T('profit concentration not measured (holdings unavailable)')
        wr_txt = T('{0} win rate on what it has sold', pct(m['winrate']))
        if m["dist_gap"]:
            wr_txt += T(' ({0:,} bought and not yet sold, so they have no realized result)',
                        m['unsettled'])
        detail = [T('{0:,} tokens, {1:,} in profit, {2}, {3}',
                     m['token_num'], m['winners'], wr_txt, pcr_txt)]
        if m["wash_refuted"]:
            top = joinsym(sym for sym, _v in m["conviction_top"])
            detail.append(T('{0} of realized gains came from size positions like {1} that netted more than their own cost basis — the profit is priced in, not churned',
                            pct(m['wash_refuted']['share']), top))
        g["G1"] = (True, detail)

    # G2 CURRENCY
    emoji, label = m["form"]
    r7 = m["roi_7d"]
    ra = m["roi_all"]
    r7t = pct(r7) if r7 is not None else "n/a"
    rat = pct(ra) if ra is not None else "n/a"
    if label in (T('broken down'), T('never worked')):
        g["G2"] = (
            False,
            T('{0} {1}: 7d {2} vs all-time {3}', emoji, label, r7t, rat),
        )
    elif r7 is not None and r7 <= 0 and m["roi_30d"] is not None and m["roi_30d"] <= 0:
        g["G2"] = (
            False,
            T('both 7d and 30d are negative ({0} / {1})', r7t, pct(m['roi_30d'] or 0)),
        )
    else:
        g["G2"] = (
            True,
            T('{0} {1}: 7d {2} vs all-time {3}', emoji, label, r7t, rat),
        )

    # G3 REACHABILITY
    cw = m["copy_window_s"]
    lat = m["latency_s"]
    reasons_fail, reasons_ok = [], []
    if m["copy_window_n"] >= 3:
        # 3x is the margin, not 1x: landing at the very edge of the window means every
        # slow block, RPC hiccup, or confirmation delay puts you on the wrong side of its exit.
        if cw < lat * 3:
            reasons_fail.append(
                T('median copy window {0} against your {1} latency — under 3x margin, it is likely already selling when you land', dur(cw), dur(lat))
            )
        else:
            reasons_ok.append(
                T('copy window {0} (your latency budget {1})', dur(cw), dur(lat))
            )
    if m["entry_n"] >= 5:
        if m["entry_p50"] > 0 and m["entry_p50"] < 30_000:
            reasons_fail.append(
                T('median entry mcap {0} — sniper/pre-graduation territory; you enter at 5–10x its cost. {1} of its entries are under $100k', mc(m['entry_p50']), pct(m['entry_sub100k']))
                + (T(' (these buys span {0:.0f} days, so this is its habit, not this week)',
                     m['span_h'] / 24) if m["span_stale"] else "")
            )
        else:
            reasons_ok.append(
                (T('entry mcap p25/p50/p75 = {0}/{1}/{2} · {3} of entries under $100k',
                   mc(m['entry_p25']), mc(m['entry_p50']), mc(m['entry_p75']), pct(m['entry_sub100k']))
                 if m['entry_sub100k'] > 0 else
                 T('entry mcap p25/p50/p75 = {0}/{1}/{2}',
                   mc(m['entry_p25']), mc(m['entry_p50']), mc(m['entry_p75'])))
            )
    for t in m["tag_info"]:
        if t["sev"] == "veto_g3":
            reasons_fail.append(T('GMGN flags it as {0} — {1}', t['name'], t['meaning']))
    if m["followers"] >= 10_000 and (m["entry_p50"] == 0 or m["entry_p50"] < 1_000_000):
        reasons_fail.append(
            T('a public identity with {0:,} followers trading small caps — copy flow has already moved the price before your order', m['followers'])
        )
    # Gas that eats a large share of the per-trade net leaves nothing for your slippage.
    if m["gas_drag"] is not None and m["gas_drag"] >= 0.25:
        reasons_fail.append(
            T('fees took {0} of the profit ({1} paid vs {2} realized), leaving {3} net per trade — no room for your slippage', pct(m['gas_drag']), usd(m['gas_total_est']), usd(m['realized_7d']), usd(m['net_per_sell']))
            if m["fee_exact"] else
            T('gas is an estimated {0} of the profit ({1:,} trades × {2} ≈ {3} vs {4} realized), leaving {5} net per trade — no room for your slippage', pct(m['gas_drag']), m['trades'], usd(m['avg_gas_usd']), usd(m['gas_total_est']), usd(m['realized_7d']), usd(m['net_per_sell']))
        )
    if m["avg_buy_usd"] > 0 and m["avg_buy_usd"] < 50:
        reasons_fail.append(
            T('average buy {0} — thin enough that fees and slippage eat the edge', usd(m['avg_buy_usd']))
        )
    if m["per_day"] > 100:
        reasons_fail.append(
            T('{0:,.0f} trades/day — bot cadence, no hand can keep pace', m['per_day'])
        )
    if m["copy_window_n"] < 3 and m["entry_n"] < 5:
        g["G3"] = (
            None,
            T('activity sample too thin — reachability not evaluated'),
        )
    elif reasons_fail:
        g["G3"] = (False, reasons_fail)
    else:
        g["G3"] = (True, reasons_ok or [T('no reachability obstacle found')])

    # G4 SURVIVABILITY
    if m["token_num"] < 5:
        g["G4"] = (None, T('sample too thin — survivability not evaluated'))
    elif len(m["honeypots"]) >= 2:
        syms = joinsym(x["sym"] for x in m["honeypots"])
        g["G4"] = (
            False,
            T('{0} live positions are honeypots ({1}, {2} that cannot be sold) — its own screening did not catch them, and copying it walks into the same ones', len(m['honeypots']), syms, usd(m['honeypot_usd'])),
        )
    elif m["lt50_share"] >= 0.35:
        g["G4"] = (
            False,
            T('{0} of its tokens are down >50% ({1:,}/{2:,}) — it does not cut', pct(m['lt50_share']), m['buckets']['lt_n50'], m['token_num']),
        )
    elif m["hold_to_zero"] is not None and m["hold_to_zero"] >= 3:
        g["G4"] = (
            False,
            T('{0} positions down 90%+ with zero sells — riding to zero is the habit', m['hold_to_zero']),
        )
    else:
        reasons = [
            T('heavy-loss share {0} ({1:,}/{2:,} down >50%)', pct(m['lt50_share']), m['buckets']['lt_n50'], m['token_num'])
        ]
        if m["hold_to_zero"] is not None:
            reasons.append(T('{0} ridden to zero (down 90%+ with zero sells)', m['hold_to_zero']))
        if m["security_checked"] and m.get("hp_refuted"):
            syms = joinsym(x["sym"] for x in m["hp_refuted"])
            mx = max(x["sells"] for x in m["hp_refuted"])
            reasons.append(T('honeypot flag checked on {0} positions: {1} hit ({2}) but each is refuted by its own fill history — one has {3:,} completed sells, and a honeypot cannot be sold. These are transfer-restricted tokenised-stock / RWA contracts — false positives', m['security_checked'], len(m['hp_refuted']), syms, mx))
        elif m["security_checked"]:
            reasons.append(T('honeypot flag checked on {0} positions, none hit', m['security_checked']))
        else:
            reasons.append(T('⚪ honeypot NOT checked (holdings unavailable) — this pass covers loss-cutting only, not honeypots'))
        g["G4"] = (True, reasons)

    # A launcher's entry timing and loss-cutting are measurements of its own token's
    # price, which it controls. Reporting them as ✅ would be reporting self-dealing
    # as skill — so they are marked unevaluated, not passed.
    if m["is_dev"]:
        na = T('launcher wallet — this measures its handling of its own token, so it does not apply')
        g["G3"] = (None, na)
        g["G4"] = (None, na)
    return g


def verdict(m, g):
    """Returns (emoji, headline, what-to-do).

    Language rules for this layer, which is the only part most readers finish:
      • The headline is a verb the reader can act on, then the cause in everyday words.
        Not "the record cannot be taken as evidence" (legalese) — "the profit is faked".
      • The action is ONE short imperative sentence. No sub-clauses, no hedging tail.
      • Colour means what it says: 🔴 measured and bad, 🟡 act differently, ⚪ not measured.
        An unmeasured gate must never render 🔴 — "we could not tell" is not "it is bad".
      • The action never restates the gate reason printed below it.
    """
    p = {k: v[0] for k, v in g.items()}

    if m["trades"] == 0:
        return ("⚪",
                T('NO READ · no trades in 7 days'),
                T('First confirm this is a wallet, not a token contract. Three checks below.'))

    if p["G1"] is False:
        if any(t["sev"] == "veto_g1" for t in m["tag_info"]):
            return ("🔴",
                    T('DO NOT COPY · the profit is self-dealt'),
                    T('Treat its P&L as if it were not there. Watch what it buys; do not use these numbers.'))
        if m["is_dev"]:
            return ("🔴",
                    T('DO NOT COPY · it is a launcher trading its own tokens'),
                    T('Do not read its trading — what matters is how many of the tokens it '
                      'launched survived. Want me to look at its launch record?'))
        if m["one_coin_note"]:
            return ("🔴",
                    T('DO NOT COPY · one token made all the money'),
                    T('Come back when it has done it again on other tokens.'))
        if m["pcr_represents_record"] and m["pcr"] is not None and m["pcr"] >= 0.75:
            return ("🔴",
                    T('DO NOT COPY · one position carried the whole result'),
                    T('Come back when it has done it again on other tokens.'))
        # Too thin to measure is ⚪, not 🔴. Nothing bad was found — nothing was found.
        # Only claim a thin sample when it IS one: this used to be the catch-all, so any
        # G1 failure the branches above did not name printed a false token count.
        if m["token_num"] < 5:
            return ("⚪",
                    T('NO READ · only {0} tokens traded', m['token_num']),
                    T('The sample is too small for any ratio to hold. Watchlist it until it has traded 5.'))
        return ("⚪",
                T('NO READ · the track record did not check out'),
                T('See the first gate below for what failed.'))

    if p["G2"] is False:
        return ("🔴",
                T('DO NOT COPY · it has stopped making money'),
                T('Re-run in 7 days to see whether it recovers or keeps sliding.'))

    # G3 and G4 are independent problems. Reporting only the first one silently drops the
    # other — a wallet you cannot get filled on AND that never cuts needs both sentences.
    if p["G1"] is None:
        return ("🟡",
                T('HOLD OFF · a wash-trading flag we cannot check'),
                T('Configure GMGN_PRIVATE_KEY and re-run. Do not size off this record first.'))
    if p["G3"] is False and p["G4"] is False:
        return ("🟡",
                T('WATCH, DO NOT COPY · you cannot get its fills, and it never cuts'),
                T('Use it only as a signal of what to look at. If you enter, set your own stop.'))
    if p["G3"] is False:
        return ("🟡",
                T('WATCH, DO NOT COPY · you cannot get its fills'),
                T('Note what it buys and at what market cap, then enter on your own terms.'))
    if p["G4"] is False:
        return ("🟡",
                T('COPY THE BUYS, NOT THE EXITS · it does not cut losses'),
                T('Take its entries and keep your own stop. Do not wait for it to sell first.'))

    if p["G3"] is None or p["G4"] is None:
        return ("🟡",
                T('HOLD OFF · one of the four was not measured'),
                (T('Its activity sample is too thin to judge reachability — this wallet barely '
                   'trades, so there is nothing to fix. Watch it until it does.')
                 if p["G3"] is None and m["sampled"] < 10 else
                 T('Read the data gap below and fix what it names, then re-run.')))

    size = usd(m["size_cap"]) if m["size_cap"] else T('your normal size')
    win = dur(m["copy_window_s"]) if m["copy_window_s"] > 0 else None
    if win:
        act = T('Start at ≤ {0}, landing within {1} of its buy.', size, win)
    else:
        act = T('Start at ≤ {0}.', size)
    return ("🟢",
            T('COPYABLE AT SMALL SIZE · all four pass'),
            act)


# ─────────────────────────── report ───────────────────────────

GATE_NAMES = {
    "G1": "AUTHENTICITY",
    "G2": "CURRENCY",
    "G3": "REACHABILITY",
    "G4": "SURVIVABILITY",
}

GATE_GLOSS = {
    "G1": "is the data trustworthy",
    "G2": "is it still earning now",
    "G3": "can you get filled",
    "G4": "does it cut losses",
}


# The card states each gate as an outcome in words a newcomer already uses. The gate's own
# name ("AUTHENTICITY") and the number behind it stay on the evidence layer: naming the
# test invites the question "how did you test it", which is exactly what the card defers.
GATE_PLAIN = {
    "G1": ("record is real", "the track record is genuine, not manufactured"),
    "G2": ("earning now", "not living off an old run"),
    "G3": ("you can keep up", "its fills are reachable at your speed"),
    # Keyed "it cuts losses", not "cuts losses": that shorter string is already the
    # numbers panel's win-rate chip, and a table keyed on English text has exactly one slot
    # per string. Reusing it silently rewrote that chip in eight fixtures.
    "G4": ("it cuts losses", "it does not ride positions to zero"),
}

# The failing form of each chip. An ❌ in front of "you can keep up" flips the icon but not
# the sentence, so the row read as four contradictions instead of four statements.
GATE_PLAIN_NEG = {
    "G1": "record may be faked",
    "G2": "not earning now",
    "G3": "you cannot keep up",
    "G4": "it does not cut losses",
}


def mark(v):
    return {True: "✅", False: "❌", None: "⚪"}[v]


# ─── style layer: main title + speed subtitle ────────────────────────────────
# Merged in from the wallet-style testbench. Four deliberate changes were made on the
# way in, each because the original mis-labelled a wallet we had already verified:
#   1. No "officially verified" badge. It fired on any non-empty `common.tags`, so it printed
#      `wash_trader` under a commendation glyph. Tags go through TAGS/severity instead.
#   2. The speed subtitle reads the MEDIAN copy window, not `avg_holding_period`. The
#      mean counts bags never sold, so it called a 2-minute scalper a 1-7 day swing trader.
#   3. P5 needs ROI > 50% plus ONE of {win rate ≥ 50%, heavy-loss share < 15%}, not all
#      three. Memecoin P&L is low-hit-rate with a fat right tail; requiring 50% win rate
#      pushed a wallet sitting at #3 on GMGN's own 7D leaderboard down to P4.
#   4. Activity-derived badges are gated on sample size (see top3_buy_share / hour_peak).
# The `token_num >= 5` floor on P5 is kept as-is: one lucky coin must not score "one-shot".

TITLES = {
    ('L4', 'P5'): ('🖨️', 'money printer',
     'machine cadence and still strongly profitable'),
    ('L4', 'P4'): ('⚙️', 'full-auto grinder',
     'thin margins, huge volume'),
    ('L4', 'P3'): ('\U0001faab', 'worn down',
     'whatever it earns, fees and slippage take back'),
    ('L4', 'P2'): ('🔥', 'gas burner',
     'high frequency, high friction; the loss is mostly cost'),
    ('L4', 'P1'): ('💥', 'self-destruct',
     'machine cadence plus broad heavy losses'),
    ('L3', 'P5'): ('🌾', 'harvester',
     'high frequency and strongly profitable — the strongest cell'),
    ('L3', 'P4'): ('⚔️', 'active winner',
     'busy hands that keep the money'),
    ('L3', 'P3'): ('🌀', 'spinning top',
     'spinning fast, going nowhere'),
    ('L3', 'P2'): ('💸', 'fee donor',
     'real volume, and the money went on-chain'),
    ('L3', 'P1'): ('🩸', 'bleeding out',
     'charging in fast with a heavy tail of big losses'),
    ('L2', 'P5'): ('🦅', 'old hunter',
     'swings rarely, earns well — the most copyable rhythm'),
    ('L2', 'P4'): ('📈', 'steady hand',
     'normal cadence, positive return, no glaring weakness'),
    ('L2', 'P3'): ('☕', 'lukewarm',
     'active, but it has not turned into anything'),
    ('L2', 'P2'): ('🐑', 'retail loser',
     'the most common cell on the board'),
    ('L2', 'P1'): ('🕳️', 'deep underwater',
     'most of its coins are down more than 50%'),
    ('L1', 'P5'): ('🗡️', 'one-shot',
     'almost never trades, and lands it when it does'),
    ('L1', 'P4'): ('🧘', 'zen winner',
     'the gain came from picks, not from working the trades'),
    ('L1', 'P3'): ('👀', 'bystander',
     'too small a sample to mean much'),
    ('L1', 'P2'): ('💧', 'toe in the water',
     'tried a few times, none worked'),
    ('L1', 'P1'): ('⚰️', 'wiped out',
     'one or two swings, wiped out'),
}


def freq_level(per_day):
    """Same boundaries as cadence_label — one concept, one set of thresholds."""
    if per_day < 1:
        return "L1"
    if per_day < 10:
        return "L2"
    if per_day <= 50:
        return "L3"
    return "L4"


def pnl_level(m):
    """P5 requires ROI > 50% and ONE corroborating shape, not all three. See note above.

    Returns (level, basis) — `basis` names the corroborator that carried P5, so the title's
    "strongly profitable" is never a bare claim. A 33%-win-rate wallet reaching P5 on its
    must not be glossed as high-hit-rate.
    """
    roi = m["roi_7d"] if m["roi_7d"] is not None else 0.0
    hits = []
    if m["winrate"] >= 0.5:
        hits.append(T('{0} hit rate', pct(m['winrate'])))
    if m["lt50_share"] < 0.15:
        hits.append(T('only {0} heavy losses', pct(m['lt50_share'])))
    if roi > 0.5 and m["token_num"] >= 5 and hits:
        return ("P5", T('7d {0} + {1}', pct(roi), hits[0]))
    if roi > 0.1:
        return ("P4", None)
    if m["lt50_share"] >= 0.40 and m["realized_7d"] < 0:
        return ("P1", None)
    if abs(roi) <= 0.10:
        return ("P3", None)
    if m["realized_7d"] < 0 or roi < 0:
        return ("P2", None)
    return ("P3", None)


def style_title(m):
    """(emoji, name, gloss, cell). None when there is nothing to label."""
    # No label on a sample that cannot carry one. The verdict already reads "no read" for a
    # sub-5-token wallet; printing "steady hand - normal cadence, positive return, no glaring
    # weakness" next to it would contradict it. Silence is the honest label here.
    if m["trades"] == 0 or m["token_num"] < 5:
        return None
    plevel, basis = pnl_level(m)
    cell = (freq_level(m["per_day"]), plevel)
    e, name, gloss_en = TITLES[cell]
    gloss = T(gloss_en)
    if basis:
        gloss += T(' ({0})', basis)
    return (e, T(name), gloss, f"{cell[0]}×{cell[1]}")


def style_speed(m):
    """(emoji, name, range) from the MEDIAN copy window — never the mean hold."""
    if m["copy_window_n"] < 3 or m["copy_window_s"] <= 0:
        return None
    s = m["copy_window_s"]
    if s < 60:
        return ("⚡", T('flash flipper'), T('< 60s'))
    if s < 86_400:
        return ("🐇", T('intraday'), T('< 24h'))
    if s < 604_800:
        return ("🧭", T('swing'), T('1–7 days'))
    return ("💎", T('long hold'), T('> 7 days'))


def spray_tail(win):
    """The copy-window clause of the spray-and-hit engine. Hoisted out of the sentence so
    the sentence stays a single translatable template rather than a concatenation."""
    if win:
        return T('You would need to land inside {0} — not achievable by hand', win)
    return T('Copying it is a race on latency, not on judgement')


def profit_engine(m):
    """(chip, one line with the numbers, what it means for copying) or None.

    Three engines, separated by two independent numbers — trade cadence and how
    concentrated the gains are. The point is not the label: it is that "speed" and
    "selection" are copied differently, and a reader who cannot tell them apart will copy
    the wrong half. Needs `holdings`; returns None rather than guessing without it.
    """
    if m["conviction_share"] is None or m["gain_top3_share"] is None:
        return None
    fast = m["per_day"] >= 50
    concentrated = m["gain_top3_share"] >= 0.5
    conv = m["conviction_share"] >= 0.6
    win = dur(m["copy_window_s"]) if m["copy_window_n"] >= 3 else None

    if fast and concentrated:
        return (
            T('🕸️ spray-and-hit'),
            T('{0:,.0f} trades/day at {1} a clip, and the top 3 winners carry {2} of the profit', m['per_day'], usd(m['avg_buy_usd']), pct(m['gain_top3_share'])),
            T('the profit comes from volume of attempts times a few hits, not from picking well. {0}', spray_tail(win)),
        )
    if fast:
        return (
            T('⚙️ turnover grind'),
            T('{0:,.0f} trades/day with profit spread thin (top 3 = {1}), median {2} net per winning exit', m['per_day'], pct(m['gain_top3_share']), usd(m['med_gain_per_exit'])),
            T('the profit is volume, and each exit is too thin to survive your slippage and fees'),
        )
    if conv and concentrated:
        return (
            T('🎯 pick-and-size'),
            T('{0:,.0f} trades/day is not fast; {1} of gains came from positions netting more than their own cost, top 3 winners = {2}', m['per_day'], pct(m['conviction_share']), pct(m['gain_top3_share'])),
            T('the profit comes from picking right and then sizing up, not from speed — this is the kind you can follow a step behind'),
        )
    return (
        T('🧩 diffuse accumulation'),
        T('{0:,.0f} trades/day, gains neither concentrated (top 3 = {1}) nor speed-driven, median {2} per winning exit', m['per_day'], pct(m['gain_top3_share']), usd(m['med_gain_per_exit'])),
        T('no single profit engine — following it means following the whole book, not any one trade'),
    )


def archetype(m):
    """Say what kind of counterparty this is, before any number gets interpreted."""
    tags = []
    if m["is_dev"]:
        tags.append(T('🏭 launcher (marks its own homework)'))
    if m["per_day"] > 50:
        tags.append(T('🤖 bot-tier {0:,.0f} trades/day', m['per_day']))
    if m["entry_n"] >= 5 and 0 < m["entry_p50"] < 100_000:
        tags.append(T('🎯 sniper, median entry {0}', mc(m['entry_p50'])))
    if m["avg_buy_usd"] >= 10_000:
        tags.append(T('🐋 whale, {0} per buy', usd(m['avg_buy_usd'])))
    if m["age_days"] is not None and m["age_days"] < 30:
        tags.append(T('🆕 new wallet, {0:.0f} days old', m['age_days']))
    if m["flip5_rate"] >= 0.3:
        tags.append(T('⚡ 5-second flipper on {0} of round trips', pct(m['flip5_rate'])))
    if m["top_pos_usd"] and m["top_pos_usd"] >= 10_000:
        tags.append(T('🏦 size-position trader, largest holding {0}', usd(m['top_pos_usd'])))
    if m["med_buys_per_pos"] and m["med_buys_per_pos"] >= 10:
        tags.append(T('🧱 ladders its size positions, median {0:,} buys each', m['med_buys_per_pos'])
                    + (T(' over {0}', dur(m['accum_window_s'])) if m['accum_window_s'] > 0 else ""))
    elif m["avg_buys_per_token"] >= 3:
        tags.append(T('🧱 scales in, {0:.1f} buys/token', m['avg_buys_per_token']))
    # 🎰 low hit rate carried by one or two outsized wins — a different animal from a
    # wallet with the same ROI and an even distribution.
    if m["winrate"] < 0.35 and m["buckets"]["gt5"] >= 1 and m["token_num"] >= 5:
        tags.append(T('🎰 lottery profile, {0} hit rate but {1} tokens above 5x', pct(m['winrate']), m['buckets']['gt5']))
    if m["avg_sells_per_token"] >= 3:
        tags.append(T('✂️ scales out, {0:.1f} sells/token', m['avg_sells_per_token']))
    # Both of the next two are None unless the sample can carry them — see the metric.
    if m["top3_buy_share"] is not None and m["top3_buy_share"] >= 0.7:
        tags.append(T('📦 concentrated bets, top 3 tokens are {0} of buy spend', pct(m['top3_buy_share'])))
    return tags


def roi_label(v):
    if v is None:
        return T('unknown')
    if v > 0.5:
        return T('strongly profitable')
    if v > 0.1:
        return T('net positive')
    if abs(v) <= 0.1:
        return T('flat')
    if v > -0.3:
        return T('net negative')
    return T('badly down')


def cadence_label(per_day):
    if per_day > 50:
        return T('bot-tier, unfollowable')
    if per_day > 10:
        return T('high freq, needs tooling')
    if per_day >= 1:
        return T('normal, hand-tradeable')
    return T('low freq, slow evidence')


def entry_label(p50):
    if p50 <= 0:
        return T('not measured')
    if p50 < 30_000:
        return T('pre-graduation, you pay up')
    if p50 < 100_000:
        return T('sniper range, no match')
    if p50 < 300_000:
        return T('small cap, heavy slippage')
    if p50 < 3_000_000:
        return T('mid cap, copyable')
    return T('large cap, deep')


def friction_label(m):
    if m["gas_drag"] is None:
        return T('not enough gas data to evaluate')
    if m["gas_drag"] >= 0.25:
        return T('friction eats the bulk')
    if m["gas_drag"] >= 0.10:
        return T('meaningful friction')
    return T('friction manageable')


def speed_read(m, g, why):
    """Three lines, each a finished thought. Nothing here requires the reader to compute."""
    rows = []
    marks = archetype(m)
    st, sp = style_title(m), style_speed(m)
    if st:
        head = f"{st[0]} {st[1]}"
        if sp:
            head += f" · {sp[0]} {sp[1]}"
        if marks:
            head += " · " + marks[0]
        rows.append((T('what it is'), head))
    else:
        rows.append((T('what it is'),
                     " · ".join(marks[:2]) if marks else T('ordinary trading wallet, no distinguishing marks')))
    key = []
    if m["per_day"] > 10:
        key.append(T('{0:,.0f} trades/day', m['per_day']))
    if m["gas_drag"] is not None and m["gas_drag"] >= 0.10:
        key.append(T('{0} net vs {1} gas', usd(m['net_per_sell']), usd(m['avg_gas_usd'])))
    if m["entry_p50"] > 0:
        key.append(T('median entry {0}', mc(m['entry_p50'])))
    if m["roi_7d"] is not None:
        key.append(T('7d {0}', pct(m['roi_7d'])))
    if m["copy_window_n"] >= 3:
        key.append(T('copy window {0}', dur(m['copy_window_s'])))
    rows.append((T('key numbers'), " · ".join(key[:4]) or T('sample too thin')))

    eng = profit_engine(m)
    if eng:
        bits = [eng[0].split(" ", 1)[-1]]
        if m["gain_top3_share"] is not None:
            bits.append(T('top 3 winners = {0}', pct(m['gain_top3_share'])))
        if m["conviction_share"] is not None:
            bits.append(T('{0} from size positions', pct(m['conviction_share'])))
        rows.append((T('profit from'), " · ".join(bits)))

    flags = [t for t in m["tag_info"] if t["sev"] in ("veto_g1", "veto_g3")] or \
            [t for t in m["tag_info"] if t["sev"] == "warn"]
    if m["honeypots"]:
        rows.append((T('top risk'),
                     T('{0} honeypots in its live book, {1} unsellable — its own screening fails too', len(m['honeypots']), usd(m['honeypot_usd']))))
    elif flags:
        rows.append((T('top risk'), f"{flags[0]['emoji']} {flags[0]['name']} · {flags[0]['meaning']}"))
    elif m["lt50_share"] >= 0.35:
        rows.append((T('top risk'),
                     T('{0} of tokens down >50% — it does not cut', pct(m['lt50_share']))))
    elif not m["security_checked"]:
        rows.append((T('top risk'),
                     T('no high-severity flags — but honeypots and the live book were not checked')))
    else:
        rows.append((T('top risk'), T('no high-severity flags')))

    return rows


def card_blocked(m, g):
    """Why the card cannot be shown, or None.

    The card's whole premise is that the reasoning is hidden, so it has nowhere to put a ⚪.
    A card with a missing tick reads as a complete verdict with one fewer reason — which is
    worse than no card, because the reader cannot see that something was not measured. So
    when the inputs are not all there, the card is withheld and the evidence layer (which
    CAN say ⚪) carries the whole answer.
    """
    if m["trades"] == 0:
        return T('no trades in the window')
    unmeasured = [k for k in ("G1", "G2", "G3", "G4") if g[k][0] is None]
    if unmeasured:
        return T('{0} not measured — the card has no way to show an unmeasured check',
                 ", ".join(T(GATE_PLAIN[k][0]) for k in unmeasured))
    if m["roi_7d"] is None:
        return T('no 7d return — the headline figure cannot be computed')
    return None



def esc(v):
    """Escape a pipe so a value can never break out of a markdown table cell."""
    return str(v).replace("|", "\\|")


def md_table(head, rows, align=None):
    """A markdown table. `head` may be a list of blanks for a two-column key/value block."""
    n = len(rows[0]) if rows else len(head)
    align = align or ["---"] * n
    out = ["| " + " | ".join(esc(h) for h in head) + " |",
           "|" + "|".join(align) + "|"]
    for r in rows:
        out.append("| " + " | ".join(esc(c) for c in r) + " |")
    return out


def caliber(m, g):
    """(emoji, label) for how good this trader is — a separate question from copyability.

    The card already answers "can you get its fills"; it did not answer "is this person any
    good", and a reader who pastes an address wants that in the first glance. Without it the
    opening was a list of ratios that a newcomer cannot rank: 69.3% and 1.2% mean nothing
    until you know whether they are excellent or ordinary. The grade puts the ranking in the
    heading so smart money reads as smart money and a losing wallet reads as one, instantly.

    It is computed from the track record ONLY — realized money, win rate, heavy-loss share,
    sample size. Reachability and loss-cutting are deliberately excluded: an unreachable
    wallet can still be an excellent trader, and collapsing the two is what a single blended
    score does wrong.
    """
    if g["G1"][0] is False or m["token_num"] < 5:
        return ("⚪", T('record unreadable'))
    ra, wr, hl, n = m["realized_all"], m["winrate"], m["lt50_share"], m["token_num"]
    if ra is not None and ra < 0:
        return ("🚮", T('loses money'))
    if g["G2"][0] is False:
        return ("📉", T('was good, not any more'))
    if ra is None:
        return ("⚪", T('record unreadable'))
    if ra >= 500_000 and wr >= 0.55 and hl <= 0.10 and n >= 50:
        return ("🏆", T('top-tier record'))
    if ra >= 100_000 and (wr >= 0.50 or hl <= 0.15) and n >= 20:
        return ("💪", T('seriously good'))
    if hl <= 0.20 and wr >= 0.40:
        return ("✅", T('solid'))
    return ("😐", T('unremarkable'))


def hook_method(m):
    """How this wallet makes its money, in four or five words. Drives the opening sentence."""
    fast = m["per_day"] >= 50
    small = 0 < m["entry_p50"] < 100_000
    if fast and small:
        return T('outrunning everyone into small caps')
    if fast:
        return T('turning over volume at machine speed')
    if m["gain_top3_share"] is not None and m["gain_top3_share"] >= 0.5:
        return T('picking a few coins and sizing into them')
    if small:
        return T('getting into small caps early')
    return T('trading steadily across a wide book')


def plain_persona(m):
    """One jargon-free sentence: what it hunts, how fast it moves, what that means for a human.

    Built from entry_p50, per_day and copy_window_s -- the same numbers the style label is
    derived from, said in the words a reader already owns. The closing clause is the point:
    a cadence figure only matters once someone tells you whether a person can match it.
    """
    bits = []
    if m["per_day"] >= 1:
        bits.append(T('{0:,.0f} trades a day', m["per_day"]))
    if m["copy_window_n"] >= 3 and m["copy_window_s"] > 0:
        bits.append(T('in and out inside {0}', dur(m["copy_window_s"])))
    if not bits:
        return None
    line = joinclause(bits)
    if m["per_day"] > 50 or (m["copy_window_n"] >= 3 and 0 < m["copy_window_s"] < 60):
        line += T(' — nobody is out-typing that')
    elif m["per_day"] < 10:
        line += T(' — a pace a person can actually match')
    return line


def _qualifier(m, chain):
    """Chain, age and following, as a tail on the record line rather than a line of its own."""
    q = [chain.upper()]
    if m["followers"] >= 10_000:
        q.append(T('{0:,} followers', m["followers"]))
    return T(' · {0}', " · ".join(q))


def card(m, g, wallet, chain):
    """Layer one: the decision and the action, with every 'how do you know' deferred.

    The opening is three lines and they carry the whole report. An earlier version led with
    "If you had followed it with $1,000 seven days ago" above the verdict, and the first
    reaction it drew was the right one: that sentence is a completed counterfactual, so it
    reads as an opportunity already missed. It also put identity fourth, meaning the first
    three lines never said why this trader was worth a reader's attention.

    So the order is now: who this is -> what their record is, in the present tense -> the
    7-day window as a *backtest that proves the trader*, not as a trade the reader failed to
    place -> and only then the verdict, which lands as the twist rather than the premise.
    """
    out = []
    emoji, headline, why = verdict(m, g)
    flags = [t for t in m["tag_info"] if t["sev"] in ("veto_g1", "veto_g3")] or \
            [t for t in m["tag_info"] if t["sev"] == "warn"]
    ident = m["twitter_name"] or (f"@{m['twitter']}" if m["twitter"] else None)

    # ── line 1: who. An anonymous address has no hook to lead with, so the verdict keeps
    #    the H1 there and the whole opening collapses by one level.
    cal_e, cal_l = caliber(m, g)
    head = (f"# {cal_e} {cal_l}　{ident}" if ident
            else f"# {cal_e} {cal_l}　{T('anonymous address')}")
    if flags:
        head += f"　`{flags[0]['emoji']} {flags[0]['name']}`"
        # Recorded so the evidence layer's flag list can skip the one the card already
        # showed, in the H1 chip and again as the card's single warning line.
        m["card_flag_name"] = flags[0]["name"]
    out += [head, ""]

    # ── line 2: the record, present tense. This is the hook: what it has actually done,
    #    stated as a standing fact rather than as a return the reader could have captured.
    if g["G1"][0] is False:
        out += ["> " + T('Its profit figures are not trustworthy — treat the track record as unknown'),
                "", _qualifier(m, chain).lstrip(" ·　").strip()]
    else:
        # The bold line carries the money and the win count and stops. Sixty-three bolded
        # characters before the first verb is a line a scanner's eye bounces off; the caveat
        # and the provenance are true but they are not the hook, so they drop one line and
        # lose the bold.
        age = (T('over {0:.0f} days', m["age_days"]) if m["age_days"] is not None
               and m["age_days"] >= 30 else None)
        if m["realized_all"] and m["realized_all"] < 0:
            head_line = T('This wallet has lost {0} {1}, {2}',
                          usd(abs(m["realized_all"])), age or T('so far'), hook_method(m))
        elif m["realized_all"]:
            head_line = T('This wallet has made {0} {1}, {2}',
                          usd(m["realized_all"]), age or T('so far'), hook_method(m))
        else:
            head_line = T('This wallet trades by {0}', hook_method(m))
        sub = [T('{0:,} of {1:,} coins in profit', m["winners"], m["token_num"])]
        if m["buckets"]["lt_n50"] is not None:
            sub.append(T('only {0:,} lost more than half', m["buckets"]["lt_n50"]))
        out += [f"**{head_line}**", joinclause(sub) + _qualifier(m, chain)]

    # ── line 3 is gone: the provenance rides on the record line above, so the 7-day figure
    #    lands on line 3 instead of line 5.
    out.append("")

    # ── line 4: the 7-day window, framed as a backtest of the trader -- present tense,
    #    and paired with what the wallet itself made so the figure reads as evidence of
    #    skill rather than as a missed entry.
    if g["G1"][0] is not False and m["roi_7d"] is not None:
        emo, label = m["form"]
        second = []
        if m["realized_7d"]:
            second.append(T('it made {0} itself this week', usd(m["realized_7d"]))
                          if m["realized_7d"] > 0 else
                          T('it lost {0} itself this week', usd(abs(m["realized_7d"]))))
        second.append(T('{0} {1} — about {2:.0f}x its long-run pace', emo, label, m["pace_x"])
                      if m["pace_x"] else f"{emo} {label}")
        lead = T('{0} follow it for a week and {1} becomes {2} ({3})', emo,
                 usd_exact(m["story_stake"]), usd_exact(m["story_out"]), pct(m["roi_7d"]))
        tail = []
        if m["realized_7d"]:
            tail.append(T('it banked {0} itself', usd(abs(m["realized_7d"])))
                        if m["realized_7d"] > 0 else
                        T('it lost {0} itself', usd(abs(m["realized_7d"]))))
        tail.append(T('{0} — about {1:.0f}x its long-run pace', label, m["pace_x"])
                    if m["pace_x"] else label)
        out += ["> **" + lead + "**", ">", "> " + joinclause(tail), ""]

    # ── line 5: the verdict. It is the turn, not the opening -- and it is never optional.
    #    Only the contrast is worth a word. An agreement connective added nothing, and in
    #    the 📉 + 🔴 case it restated: "was good, not any more" and "it has stopped making
    #    money" are one finding from one gate, so "and" made them read as two. A neutral
    #    grade establishes no direction to agree or disagree with, and an unknown one
    #    nothing at all -- both take no connective.
    CAL_GOOD = ("🏆", "💪", "✅")
    link = (T('but ') if cal_e != "⚪" and emoji != "⚪"
            and (cal_e in CAL_GOOD) != (emoji == "🟢") else "")
    out += [f"## {emoji} {link}{headline}", ""]
    persona = []
    if m["gain_top3_share"] is not None and g["G1"][0] is not False:
        persona.append(T('{0} of the money came from just 3 coins — copying it randomly '
                         'mostly misses them', pct(m["gain_top3_share"]))
                       if m["gain_top3_share"] >= 0.5 else
                       T('the money is spread across many coins (top 3 = {0}), so no single '
                         'copy decides it', pct(m["gain_top3_share"])))
    pp = plain_persona(m)
    if pp:
        out += [pp, ""]
    if persona:
        out += [" · ".join(persona), ""]

    # ── the action ──
    # A red verdict gets the verdict's own instruction, never a sizing and a copy window:
    # those are directions for FOLLOWING, and printing them under DO NOT COPY is the card
    # telling the reader to do the thing its own headline just told them not to.
    unreachable = g["G3"][0] is False
    if emoji == "🔴":
        out += ["## " + T('  WHAT TO DO').strip(), "", why, ""]
    elif unreachable:
        if m["size_cap"]:
            out += [T('Even at its own pace, anything over {0} moves the price against you.',
                      usd_exact(m["size_cap"])), ""]
        out += [why, ""]
    else:
        out += ["## " + T('  HOW TO FOLLOW').strip(), ""]
        cells, heads = [], []
        if m["size_cap"]:
            heads.append(T('start no larger than'))
            cells.append(f"**{usd_exact(m['size_cap'])}**")
        if m["copy_window_n"] >= 3 and m["copy_window_s"] > 0:
            heads.append(T('get your order in within'))
            cells.append("**" + T('{0} of its buy', dur(m["copy_window_s"])) + "**")
            if m["span_stale"]:
                stale_note = T('measured across {0:.0f} days of its trades, not just this week',
                               m['span_h'] / 24)
        if cells:
            out += md_table(heads, [cells]) + [""]
            if m["span_stale"] and m["copy_window_n"] >= 3 and m["copy_window_s"] > 0:
                out += [stale_note, ""]
        if m["size_ratio"]:
            out += [(T('the {0} you asked about is {1:.1f}x its own clip of {2} — at that '
                       'size your fills are worse than the ones this record was built on',
                       usd_exact(m["my_size"]), m["size_ratio"], usd_exact(m["avg_buy_usd"]))
                     if m["my_size"] > m["size_cap"] else
                     T('the {0} you asked about is within that', usd_exact(m["my_size"]))), ""]
        if m["copy_window_n"] >= 3 and m["copy_window_s"] > 0:
            out += [(T('under a minute — you need automated copy-trading for this; clicking '
                       'by hand you will not make it')
                     if m["copy_window_s"] < 60 else
                     T('wide enough to place by hand, if you are watching')), ""]
            out += [T('past that, let it go — its cost is lower than yours, and entering '
                      'late means buying what it is selling'), ""]

    # Read the gates. These were hardcoded to "✓" in the first cut, which put
    # "✓ the record is real" on a card whose verdict was DO NOT COPY *because* that check
    # failed — the card asserting the opposite of its own headline.
    chips = []
    for k in ("G1", "G2", "G3", "G4"):
        if g[k][0] is True:
            chips.append("✅ " + T(GATE_PLAIN[k][0]))
        elif g[k][0] is False:
            chips.append("❌ **" + T(GATE_PLAIN_NEG[k]) + "**")
    if chips:
        out += ["　".join(chips), ""]

    if flags:
        out += ["> ⚠️ " + flags[0]["meaning"], ""]

    if m["recent_buys"]:
        out += ["## " + T('  BOUGHT IN THE LAST 24H').strip(), ""]
        for sym_, v_, mc_ in m["recent_buys"][:3]:
            out.append(f"- {sym_} **{usd(v_)}**"
                       + (T(', bought at {0} mcap', mc(mc_)) if mc_ else ""))
        out.append("")

    if m["idle_s"] is not None:
        out += [(T('⚠️ Its last trade was {0} ago — every figure here describes a wallet that '
                   'has since gone quiet.', dur(m["idle_s"])) if m["stale"]
                 else T('Last trade {0} ago.', dur(m["idle_s"]))), ""]

    if m["open_value"] and m["open_book"]:
        top = m["open_book"][0]
        # "Not a wallet that only churns" was a defence against a churn accusation. Now that
        # the report never puts that accusation on the page, the defence answers a charge the
        # reader never saw -- and it was editorial either way. The facts stand alone.
        out += [T('It is still holding {0} coins worth {1} — biggest is {2} at {3}.',
                  m["holdings_n"], usd(m["open_value"]), top["sym"], usd(top["usd"])), ""]
    out += ["> " + T('⚠️ A track record is past behaviour. It is not a forecast, and none of '
                     'this is advice — size it yourself.'), ""]
    return out


def report(wallet, chain, m, g, gaps, brief=False):
    """Two layers of native markdown, in reading order.

    Layer one is the decision: verdict, the return told as money, who this is, what to do.
    Layer two is the evidence behind every one of those claims. The split exists because
    the two audiences are different and were fighting over the same screen — a newcomer
    needs to stop reading after the card, and whoever is checking the work needs every
    number.

    The output is markdown rather than column-aligned terminal text, because the places it
    is actually read — chat, an agent pipeline, a doc — do not render in a monospace grid,
    and a hand-built column of spaces shears the moment they do not. Tables align
    themselves; nothing here depends on a 76-column assumption.
    """
    out = []
    w = wallet if len(wallet) <= 14 else f"{wallet[:6]}…{wallet[-4:]}"
    emoji, headline, why = verdict(m, g)

    blocked = card_blocked(m, g)
    if not blocked:
        out += card(m, g, wallet, chain)
        out += ["---", ""]
        if brief:
            # Nothing follows in brief mode, so the "below:" signpost would point at an
            # empty page. The footer is the only line that still applies.
            out += [T('Everything above measures behaviour that already happened. Not a prediction, not advice.')]
            return "\n".join(out)
        out += [T('Every claim above is backed by a number. Below: what each of the four '
                  'checks tested, and the number that decided it.'), ""]
        out += ["---", "", "# " + T('EVIDENCE'), ""]
    elif brief:
        # Asked for the card, cannot honestly produce one. Say why rather than emitting a
        # card with a hole in it, and hand back the full report instead of nothing.
        out += ["> **" + T('NO CARD  ').strip() + "** " + blocked, ""]

    if blocked:
        # No card was printed, so the verdict has not been stated yet — it leads here.
        out += [f"# {emoji} {headline}", "",
                f"**{T('DO THIS  ').strip()}** {why}", ""]
    out += ["`" + T('{0} · {1} · window 7d (all-time from profits --period all)', w, chain) + "`",
            ""]

    if m["trades"] == 0:
        out += ["## " + T('NEXT'), ""]
        for step in (
            T('Confirm this is a wallet, not a token contract — a contract queries fine and returns zeros everywhere, which looks like an answer and is not one.'),
            T('Confirm the chain: base58 → sol, 0x → bsc/base/eth.'),
            T('If it is a wallet, check whether it only ever received transfers or airdrops '
              'rather than trading. Want me to look at what it holds?'),
        ):
            out.append(f"- {step}")
        if gaps:
            out += ["", "## " + T('DATA GAPS:'), ""] + [f"- ⚪ {gp}" for gp in gaps]
        return "\n".join(out)

    if blocked:
        out += ["## " + T('⚡ SPEED READ'), ""]
        out += [f"- **{lab}** — {val}" for lab, val in speed_read(m, g, why)] + [""]

    # ── identity ────────────────────────────────────────────────────────────────
    rows_id = []
    st, sp = style_title(m), style_speed(m)
    if st:
        head = f"{st[0]} **{st[1]}**"
        if sp:
            head += T(', {0}{1}, holds for {2} typically', sp[0], sp[1], sp[2])
        rows_id.append((T('style'), [head, st[2]]))

    if m["twitter_name"] or m["twitter"]:
        bits = [(f"{m['twitter_name'] or ''} @{m['twitter']}" if m["twitter"]
                 else m["twitter_name"]).strip()]
        if m["blue"]:
            bits.append(T('blue-verified'))
        if m["followers"]:
            bits.append(T('{0:,} followers', m['followers']))
        acct = " · ".join(bits)
        # Spell the profile out. Someone who searched this address wants to know whose
        # account it is, and a bare @handle still leaves them to go and find it.
        # The card carries the handle and follower count; only the profile URL is new here.
        if blocked:
            rows_id.append((T('account'),
                            [acct] + ([f"x.com/{m['twitter']}"] if m["twitter"] else [])))
        elif m["twitter"]:
            rows_id.append((T('account'), f"x.com/{m['twitter']}"))
    elif not (m["tags"] or m["fund_from"] or m["fund_from_address"]):
        rows_id.append((T('account'),
                        T('no X account bound and no traceable funding source — an anonymous address')))
    else:
        rows_id.append((T('account'), T('no X account bound (no public identity on GMGN)')))

    prov = [f"{t['emoji']} {t['name']}" for t in m["tag_info"] if t["sev"] == "neutral"]
    if m["age_days"] is not None:
        prov.append(T('{0:.0f}-day-old wallet', m['age_days']))
    if m["native_balance"] > 0:
        prov.append(T('{0:,.1f} {1} on hand', m["native_balance"], NATIVE.get(chain, chain.upper())))
    if m["fund_from"] or m["fund_from_address"]:
        src = m["fund_from"] or f"{m['fund_from_address'][:6]}…"
        prov.append(T('funded from {0}', src)
                    + (f" {usd(m['fund_amount'])}" if m["fund_amount"] else ""))
    if m["dev_total"]:
        prov.append(T('launched {0} tokens ({1} graduated · {2})', m['dev_total'], m['dev_open'], pct(m['dev_open_ratio'])))
    elif m["created_tokens_n"]:
        prov.append(T('launched {0} tokens', m['created_tokens_n']))
    if prov:
        rows_id.append((T('provenance'), " · ".join(prov)))

    marks = archetype(m)
    if marks:
        rows_id.append((T('marks'), " · ".join(marks)))

    eng = profit_engine(m)
    if eng:
        chip, detail, meaning = eng
        # The card states the chip and what it means for copying. Only the numbers behind it
        # are new down here, so that is all this row carries when a card was printed.
        rows_id.append((T('engine'), [f"**{chip}**", detail] if not blocked
                                     else [f"**{chip}**", detail, f"→ {meaning}"]))

    if rows_id:
        out += ["## " + T('👤 WHO IT IS'), ""]
        for k, v in rows_id:
            vals = v if isinstance(v, list) else [v]
            out.append(f"- **{k}** — {vals[0]}")
            # Two-space indent keeps a continuation line inside its list item instead of
            # starting a new paragraph, which is what `<br>` was standing in for.
            out += [f"  {extra}" for extra in vals[1:]]
        out.append("")

    # ── the four gates ──
    out += [f"## 🚦 {T('THE FOUR GATES')}", ""]
    for k in ("G1", "G2", "G3", "G4"):
        out += [f"### {mark(g[k][0])} {T(GATE_GLOSS[k])}", ""]
        detail = g[k][1]
        for item in (detail if isinstance(detail, list) else [detail]):
            out.append(f"- {item}")
        out.append("")

    # ── risk flags: binary facts, no paragraph to parse ──
    shown = m.get("card_flag_name") if not blocked else None
    risk = [f"{t['emoji']} **{t['name']}** · {t['meaning']}"
            for t in m["tag_info"] if t["sev"] in ("veto_g1", "veto_g3", "warn")
            and t["name"] != shown]
    if m["honeypots"]:
        risk.append(T('🍯 {0} honeypot positions ({1}) · {2} unsellable',
                      len(m['honeypots']), joinsym(x["sym"] for x in m["honeypots"]),
                      usd(m['honeypot_usd'])))
    good = [f"{t['emoji']} **{t['name']}** · {t['meaning']}"
            for t in m["tag_info"] if t["sev"] == "good"]
    # A clean screen is reassurance, not a risk — it must not inflate the risk count.
    if not m["honeypots"] and m["security_checked"] and m.get("hp_refuted"):
        good.append(T('✅ {0} honeypot flags ({1}) refuted by fill history — the busiest has {2:,} completed sells; transfer-restricted tokenised stocks, not honeypots',
                      len(m['hp_refuted']), joinsym(x["sym"] for x in m["hp_refuted"]),
                      max(x["sells"] for x in m["hp_refuted"])))

    out += [("## " + T('🚩 RISK FLAGS ({0})', len(risk))) if risk
            else ("## " + T('✅ NO RISK FLAGS')), ""]
    out += [f"- {r}" for r in risk] + [""]
    if good:
        out += ["**" + T('CLEARED') + "**", ""] + [f"- {gd}" for gd in good] + [""]

    # ── core figures: only on the blocked path, where no card printed them ──
    # The full numbers panel and the outcome-distribution chart were deleted. Every figure
    # that decides something is printed by the gate that decided it; the panel restated those
    # and added eight rows of reference (all-time realized, fee share, entry quartiles, clip
    # size, mean hold, bucket histogram) that a reader consults but never acts on. The
    # mean-vs-median warning went with it -- its subject, the API's mean hold, is no longer
    # printed anywhere, so there is no contradiction left to reconcile.
    if blocked:
        core = [T('7d {0}', pct(m['roi_7d'])) if m["roi_7d"] is not None else None,
                T('all {0}', pct(m['roi_all'])) if m["roi_all"] is not None else None,
                T('{0:,.0f}/day', m["per_day"]),
                T('win {0}', pct(m['winrate'])),
                T('entry {0}', mc(m['entry_p50'])) if m["entry_p50"] else None]
        out += [" · ".join(c for c in core if c), ""]
    if m["one_coin_note"]:
        out += [f"> ⚠️ {m['one_coin_note']}", ""]

    # ── what it is doing now ──
    pe, pl = m["posture"]
    out += ["## " + T('🔄 WHAT IT IS DOING NOW'), "",
            T('{0} **{1}** · 24h bought {2} / sold {3}', pe, pl, usd(m['buy_usd_24h']), usd(m['sell_usd_24h']))]
    if m["idle_s"] is not None and blocked:
        out.append((("> ⚠️ " + T('last trade {0} ago — every figure here describes a wallet that '
                                 'has since gone quiet', dur(m["idle_s"]))) if m["stale"]
                    else T('last trade {0} ago', dur(m["idle_s"]))))
    out.append("")
    extra = m["recent_buys"] if blocked else []
    if extra:
        out += ["**" + (T('bought in 24h') if blocked
                        else T('also bought in 24h')).strip() + "**", ""]
        out += [f"- {sym} **{usd(v)}**" + (T(', bought at {0} mcap', mc(mc_)) if mc_ else "")
                for sym, v, mc_ in extra] + [""]
    if m["open_book"]:
        if blocked:
            out += ["**" + T('{0} positions · {1} total', m['holdings_n'], usd(m['open_value'])) + "**", ""]
        hp_syms = {x["sym"] for x in m["honeypots"]}
        out += md_table([T('token'), T('market value'), T('P&L'), T('sells')],
                        [[bk["sym"] + (" 🍯" if bk["sym"] in hp_syms else ""),
                          usd(bk["usd"]), pct(bk["chg"], 0), f"{bk['sells']:,}"]
                         for bk in m["open_book"][:5 if blocked else 3]],
                        ["---", "---:", "---:", "---:"]) + [""]
    else:
        out += [T('live book: unavailable (see data gaps)'), ""]

    # ── what to do next ──
    out += ["## " + T('✅ WHAT TO DO NEXT'), ""]
    out += [f"- {a}" for a in actions(m, g, card_shown=not blocked)] + [""]

    out += ["---", ""]
    cap = (T(' (hit page cap — busiest slice only)') if m["hit_limit"]
           else (T(' — sparse: {0} rows stretched over {1:.0f} days', m['sampled'], m['span_h'] / 24)
                 if m["span_stale"] else ""))
    out.append("`" + T('sample  {0:,} activity rows / {1} tokens · spans {2:.1f}h{3}',
                       m['sampled'], m['distinct_tokens_sampled'], m['span_h'], cap) + "`")
    if gaps:
        out += ["", "**" + T('DATA GAPS (unevaluated ≠ passed):') + "**", ""]
        out += [f"- ⚪ {gp}" for gp in gaps]
    out += ["", T('Everything above measures behaviour that already happened. Not a prediction, not advice.')]
    return "\n".join(out)



def actions(m, g, card_shown=False):
    """Three follow-up questions, in the reader's words.

    This section used to be conditional advice — size caps, copy windows, "set your own
    stop" — which duplicated the card and stacked several intents into one bullet. All of
    that already has a home: the card gives the instructions, the gates give the reasoning.
    What is missing at the end of a dossier is simply the next question, so this now prints
    exactly three of them and nothing else. Each is one intent, phrased the way the reader
    would ask it, so their own follow-up routes itself to whichever skill answers it.

    Every candidate must be answerable by a skill that exists in GMGNAI/gmgn-skills. A
    question with no skill behind it is worse than no question: the reader asks it, nothing
    can answer, and the dossier has sent them into a wall. Two candidates were cut for
    exactly that reason — "which coins made this week\'s money" (portfolio profits returns
    one aggregate row per period, never a per-token breakdown) and "check back in a week"
    (a reminder, not a query). The skill each surviving question routes to is named beside
    it below; keep that mapping accurate when adding one.
    """
    if m["trades"] == 0:
        # -> gmgn-token info: a contract address answers here, a wallet does not.
        return [T('Is this address a wallet at all, or a token contract?')]

    # Ordered by how much this particular wallet's data invites the question; first three win.
    # The first three are deliberately three different skills.
    pool = []
    top_buy = m["recent_buys"][0][0] if m["recent_buys"] else ""
    if top_buy:
        # -> gmgn-holder-analysis
        pool.append(T('What do the chips look like on {0} — who is holding, and at what cost?', top_buy))
    # -> gmgn-wallet-score, copy-tradeability angle
    pool.append(T('Score it 0-100 with my own latency and slippage modelled in?'))
    if m["created_tokens_n"] > 0:
        # -> gmgn-wallet-score, Dev-reputation angle
        pool.append(T('It launched {0} tokens — how many of them are still alive?',
                      f'{m["created_tokens_n"]:,}'))
    if top_buy:
        # -> gmgn-kline-pattern
        pool.append(T('What shape is {0} in right now — still climbing, or already breaking down?',
                      top_buy))
        # -> gmgn-token security
        pool.append(T('Are the contracts on {0} safe — honeypot, liquidity, mint authority?', top_buy))
        # -> gmgn-token (smart-money / KOL positions) or gmgn-track
        pool.append(T('Who else is buying {0} — any smart money or KOLs in there?', top_buy))
    if m["holdings_n"]:
        # -> gmgn-portfolio holdings
        pool.append(T('It holds {0} coins — list the whole book with costs?', f'{m["holdings_n"]:,}'))
    return pool[:3]


# ─────────────────────────── entry ───────────────────────────


def main(argv):
    args = [a for a in argv[1:]]
    latency_s, my_size, fixture, brief = 3.0, None, None, False
    rest = []
    k = 0
    while k < len(args):
        if args[k] == "--latency" and k + 1 < len(args):
            latency_s = f(args[k + 1], 3.0)
            k += 2
        elif args[k] == "--size" and k + 1 < len(args):
            my_size = f(args[k + 1])
            k += 2
        elif args[k] == "--brief":
            brief = True
            k += 1
        elif args[k] == "--fixture" and k + 1 < len(args):
            fixture = args[k + 1]
            k += 2
        else:
            rest.append(args[k])
            k += 1

    # English is the default. Chinese is a deliberate choice the caller makes by passing `zh`
    # -- SKILL.md tells the agent to pass it whenever the user wrote in Chinese -- so a bare
    # invocation from a pipeline, a cron job or another skill comes out in English.
    lang = next((x for x in rest if x in ("zh", "en")), "en")
    load_lang(lang)
    rest = [x for x in rest if x not in ("zh", "en")]

    gaps = []
    if fixture:
        with open(fixture) as fh:
            d = json.load(fh)
        wallet = d.get("_wallet", "FIXTURE")
        chain = d.get("_chain", "sol")
        gaps += d.get("_gaps", [])
    else:
        if len(rest) < 2:
            print(__doc__)
            return 2
        wallet, chain = rest[0], rest[1]
        try:
            d = collect(chain, wallet, gaps)
        except Gap as e:
            print(
                T('Data pull failed, no verdict possible: {0}\nCheck `gmgn-cli config --check` first; on 429 wait for the stated reset; on 401/403 with valid credentials check IPv6 (gmgn-cli is IPv4 only).', e)
            )
            return 1

    m = compute(d, latency_s, my_size)
    g = gates(m)
    print(report(wallet, chain, m, g, gaps, brief))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
