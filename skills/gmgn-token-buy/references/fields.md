# gmgn-cli 命令与字段

> 本技能读取的全部命令与 JSON 字段。SKILL.md 的流程只在这里取字段名，**不在这份清单里的字段一律当作不存在**。

**全部数据只经 `gmgn-cli` 取。** 不抓网页、不接第三方源、不自己拼 HTTP 请求。API Key 由 CLI 自己从本机配置读取并签发，**本技能不读、不存、不传任何凭证**；下面四条命令全是读接口，只需 API Key，不需要私钥（私钥只有 gmgn-swap 下单才用）。

- **只覆盖 7 条链**：`sol` `eth` `bsc` `base` `robinhood` `arc` `stable`。其余链一律硬停、不下单。
- **限流**：漏桶 20 次/秒。**单币尽调固定 4 个请求，与同名候选有多少个无关**（见下面的搜币说明），碰不到限流。被限返回 `RATE_LIMIT_BANNED` + `reset_at`（Unix 秒）。**读 `reset_at` 等到解封再试，期间绝不重试**——每重试一次封禁延长 5 秒（最多 5 分钟）。

## 命令

| 用途 | 命令 | 关键字段 |
|---|---|---|
| 按名/符号/CA 搜币 | `gmgn-cli market search -q <名字或CA> [--chain <链>] --order-by weight --raw` | 见下 |
| 行情/深度/持仓/风险 | `gmgn-cli token info --chain <链> --address <CA> --raw` | 见下 |
| 安全审查 | `gmgn-cli token security --chain <链> --address <CA> --raw` | 见下 |
| gas + 原生币价 | `gmgn-cli gas-price --chain <链> --raw` | 见下 |

`gas-price` 是**顶层**命令，不在 `swap` 或 `market` 下面。查不到某条链时报"需手填"，不要换命令硬试。

## `market search` 字段映射（一次调用拿全部候选）

⚠️ **只读 `coins[]`，`wallets[]` 与本技能无关。** 同一次响应会同时返回钱包命中，且数量常常比代币还多——实测用 PEPE 的合约地址去搜，返回 `coins` 1 条、`wallets` 10 条；用一个不存在的地址去搜，返回 `coins` 0 条、`wallets` 11 条。**`wallets` 非空绝不能当成"找到了这个币"**，判断"有没有搜到"只看 `coins` 的长度。地址搜索本身是精确的：真实 CA 稳定返回恰好 1 条 `coins`（PEPE、BONK 实测）。

**关键**：`coins[]` 的每一行都自带筛选所需的全部数字，且与 `token info` 的对应字段**逐字节相同**（已用 PEPE 核对：`liquidity` / `volume_24h` / `swaps_1h` / `swaps_24h` / `holder_count` 四项完全一致）。所以**同名候选无论 60 个还是 100 个，排序与粗筛都在这一次调用里做完，不要给每个候选各打一次 `token info`**——那是几十倍的请求量，也会撞限流。只有最终锁定的那一个才继续走 `token info` + `token security`。

| 用途 | 字段 |
|---|---|
| 链 / 合约 / 名称 / 符号 | `chain` / `address` / `name` / `symbol` |
| 流动池（**两侧之和**，见下警告） | `liquidity` |
| 交易量 / 成交笔数 | `volume_24h` / `volume_1h` / `swaps_5m` / `swaps_1h` / `swaps_6h` / `swaps_24h` |
| 市值 / 历史最高市值 | `mcp` / `ath_market_cap` |
| 持有人数 | `holder_count` |
| 存续时长 | `created_at`（Unix **秒**）。⚠️ 可能是 `0` = 未知（实测真 BONK 就是 `0`），此时跳过存续加成，不要算成 1970 年 |
| 买 / 卖税 | `buy_tax` / `sell_tax` / `total_buy_tax` / `total_sell_tax`（空串=未测，不当 0） |
| 蜜罐初筛 | `is_honeypot`（三态，常为 `null`；权威判定仍走 `token security`） |
| 仿盘 / 改名信号 | `twitter_rename_count` / `twitter_change_flag` / `cto_flag` / `kol_count` / `is_og` |
| 发行方 | `creator`（要查发行方历史时直接用它，不必先打 `token info`） |
| 发射台 | `launchpad_platform` / `launchpad_status` / `progress` |

⚠️ **`liquidity` 是池子两侧储备之和，约等于可交易深度的 2 倍**（PEPE 实测：`liquidity` $26.6M，而 `min(base_reserve_value, quote_reserve_value)` = $13.27M）。**`thresholds.md` 的深度门槛是单边口径，不能直接套在 `liquidity` 上**；候选粗筛时用 `liquidity / 2` 近似，最终闸门用 `token info` 的单边口径（取法与三条陷阱见本文）。

⚠️ `--order-by weight` 会由服务端按相关度排序并**丢掉蜜罐**——这是便利，**不是安全闸门**，安全仍以 `token security` 为准。

⚠️ `--chain all` 上游不认（会返回空结果），CLI 已代为改成"省略链参数搜全链"并在 stderr 提示。想搜全链就**直接不给 `--chain`**。搜不到结果时**不要断言"这个币不存在"**——它同样可能在不支持的链上、或名字拼错了。

⚠️ `ath_market_cap` 在极新、极低供应量的币上会给出荒谬数值（实测见过 $345 万亿）。它只能当"曾经到过的量级"参考，**不进任何闸门**。

## `token info` 字段映射（只对最终锁定的那一个币调用）

| 用途 | 字段 |
|---|---|
| 可交易深度（单边口径） | 两侧都 > 0 时取 `min(pool.base_reserve_value, pool.quote_reserve_value)`；**任一侧为 `"0"` 或缺失时改用 `pool.liquidity / 2`**（见下方 ⚠️） |
| 24h 成交额 / 各窗口 | `price.volume_24h` / `volume_1h` / `buys_1h` / `sells_1h` / `swaps_1h` |
| **方向与波动**（「三、」闸用） | `price.price` / `price.price_5m` / `price.price_1h` / `price.price_24h`（各窗口**起点价**）；`price.buy_volume_5m` / `sell_volume_5m` / `buy_volume_1h` / `sell_volume_1h` / `buy_volume_24h` / `sell_volume_24h`（买卖分开的成交额） |
| 交易者画像（警告项用） | `stat.top_entrapment_trader_percentage`（诱捕）/ `stat.top_bot_degen_percentage`（机器人）/ `stat.fresh_wallet_rate`（新钱包）/ `wallet_tags_stat.bundler_wallets`（捆绑钱包**个数**，要自己除以 `holder_count`）/ `wallet_tags_stat.smart_wallets` / `whale_wallets` |
| 主池 DEX 类型（EVM gas 用量用） | `pool.exchange`（如 `uniswap_v4`、`pancake_v2`） |
| **蜜罐第 4 层判据** | `price.sells_24h > 0` → 有真实卖出即非蜜罐 |
| 市值 | `price.price × circulating_supply`（无直接市值字段） |
| 持有人数 | `holder_count` |
| 开发者持仓 | `stat.creator_hold_rate` —— 这才是开发者当前持仓比例；**`dev.top_10_holder_rate` 是「Top10 里开发者相关地址占比」，不是开发者持仓**，两者混用会误判 |
| 开发者 | `dev.creator_token_status`（`creator_close`=已清仓）/ `dev.top_10_holder_rate` / `dev.twitter_name_change_history`（改名=跑路信号） |
| 风险画像 | `stat.top_rat_trader_percentage`（老鼠仓）/ `top_bot_degen_percentage`（机器人）/ `top_bundler_trader_percentage`（捆绑）/ `top70_sniper_hold_rate`（狙击） |
| 创建时间 | `creation_timestamp`（Unix **秒**）。⚠️ **可能是 `0`**，那是"未知"而不是 1970 年——实测 BONK 的 `creation_timestamp` 与 `open_timestamp` 都是 `0`，直接拿它算存续会得出 56 年。取到 `0` 就把存续时长记为未知，跳过存续加成，**绝不能当成"老盘"给加分**。 |

⚠️ **主池某一侧的折美元储备可能是 `"0"`，而池子完全正常。** 实测 BONK 主池（meteora_dlmm）`base_reserve_value` = `"0"`、`quote_reserve_value` = `$41,687`——上游没给 BONK 那一侧定价，不是池子里没有 BONK（`base_reserve` 有 147 亿枚）。此时 `min()` 会算出 $0 深度，把一个百万持有人的蓝筹判成"深度不足"，这是把**数据缺失误当风险结论**。所以：两侧都 > 0 时取较小值（更保守），**任一侧为 0 或缺失时退回 `pool.liquidity / 2`**。

⚠️ **`pool.liquidity` 恒等于某一侧储备的 2 倍，但是哪一侧不可预测**——实测 PEPE / SHIB / BONK / PENGU / BRETT 都是 `2 × quote`，而 CAKE 是 `2 × base`（按 `2 × quote` 算会偏低 12%）。所以只能用 `liquidity / 2` 这一个式子取单边口径，不要去猜是哪一侧。六个币实测 `liquidity / 2` 与双边取小的偏差都在 0.4% 以内（CAKE 因上述原因偏高 13.7%，方向是不保守的，这也是"两侧都有值时优先用 min()"的原因）。

⚠️ **`pool` 返回的不一定是最深的池。** 实测 BONK 的 `biggest_pool_address` = `Bqnp…JGez`，而 `pool.pool_address` = `31p1…W777`，两者不同。所以这个深度是**下限**：`biggest_pool_address ≠ pool.pool_address` 时要在候选表里标注"深度为下限"，**不能因为它偏低就判死**。相应地，**24h 成交额远大于池深度是"这个币还有别的池"的正常信号，不是刷量**（BONK 实测主池深度 $41.7K、24h 成交 $507K，比值 12）——这一条优先于`thresholds.md` 一、里的量/深度比值上限。GMGN 无"列全部池"的端点，多池分散的币深度只能偏保守。

## `token security` 字段映射 + 蜜罐四层

| 用途 | 字段 | 适用链 |
|---|---|---|
| 蜜罐（四层：任一有值即用） | ① `is_honeypot` → ② `honeypot` 整数(0安全/1蜜罐/−1未测) → ③ `can_not_sell=1` → ④ 上面 info 的 `sells_24h>0` | 两链 |
| 买 / 卖税 | `buy_tax` / `sell_tax`（空串=未测，不当成 0） | 两链 |
| Top10 持仓 | `top_10_holder_rate` | 两链 |
| 合约权限已放弃 | `is_renounced` / `renounced` | **仅 EVM** |
| 开源 | `is_open_source` | **仅 EVM** |
| 增发权限已撤 | `renounced_mint` | **仅 Solana** |
| 冻结权限已撤 | `renounced_freeze_account` | **仅 Solana** |
| 锁仓 / 销毁 | `lock_summary.is_locked` + `lock_percent`（**必须一起读**）/ `lock_detail[].is_blackhole`（黑洞=已销毁） | 两链 |

🚨 **这几个字段是分链的，跨链读会把蓝筹币误判成风险币。** 实测对照：

| 字段 | PEPE（eth） | BONK（sol） |
|---|---|---|
| `is_renounced` / `is_open_source` | `true` / `true` | **`null`** |
| `renounced_mint` / `renounced_freeze_account` | **`false`** | `true` |
| `honeypot` | `-1`（未测） | `0`（安全） |

- **在 EVM 上，`renounced_mint` / `renounced_freeze_account` 恒为 `false`，这是"该链没有这个概念"，不是"权限没放弃"。** 拿它当扣分项会直接把 PEPE 这种币拦下。EVM 看 `is_renounced`。
- **在 Solana 上，`is_renounced` / `is_open_source` 恒为 `null`。** 按三态规则记 `None`（未知），**不算不通过**，也不要因此判"数据缺失"。Solana 看 `renounced_mint` / `renounced_freeze_account`。
- **`is_locked=true` 单独没有意义**——PEPE 实测 `is_locked=true` 而 `lock_percent=0.00009`（约 0%）。必须读 `lock_percent`。
- **蓝筹币的 `honeypot` 也可能是 `-1`（未测）**——PEPE 实测就是。所以四层回退是必需的，不是冗余；`honeypot=-1` 只是"没测"，配合 `can_not_sell=0` 与 `sells_24h>0` 才能下"非蜜罐"的结论。

**三态映射**：字段缺席、为 `null` 或空串一律 `None`（未知），绝不退化成 `False`/`0`——否则"未检测"会显示成"蜜罐否 / 0% 税 / 已弃权"，把空白包装成安全。**判"数据缺失、不能买"要按该链应有的字段数来数**，别拿 EVM 的字段清单去数一个 Solana 币。

⚠️ **`price` 块里的 `price_5m` / `price_1h` / `price_24h` 是那个窗口的「起点价」，不是涨跌幅。** 涨跌幅要自己算：`price / price_5m − 1`。实测 robinhood 上的 MEME `price` = 0.0924、`price_5m` = 0.1107，也就是 5 分钟 −16.5%——而同一响应的 `volume_24h` 是 $63.14M。**只读成交额看不出这件事**，这就是「三、方向与波动」这道闸存在的原因。

⚠️ **`wallet_tags_stat` 给的是钱包「个数」，`stat.*_percentage` 给的是百分比，不要混。** 实测 MEME `wallet_tags_stat.bundler_wallets` = 971、`fresh_wallets` = 1000、`smart_wallets` = 198、`whale_wallets` = 49，而 `holder_count` = 11,423——捆绑占比要自己算成 8.5%。注意 `fresh_wallets` = 1000 看着像被截顶在 1000，所以新钱包比例优先读 `stat.fresh_wallet_rate`（实测 13.81%），不要拿这个数去除。

⚠️ **`lock_summary` 内部可以自相矛盾，三个字段都要读。** 实测 MEME：`is_locked` = `true`、`lock_percent` = `"0"`、而 `lock_detail[0]` 是 95% 打进黑洞地址 `0x000…0`。`lock_percent` = 0 配 `is_locked` = true 不是「没锁」，是**上游没把销毁算进锁仓比例**。判定顺序：先看 `lock_detail[].is_blackhole`（黑洞=已销毁，最硬）→ 再看 `lock_percent` → `is_locked` 单独永不作为依据。三者冲突时按 `lock_detail` 判，并在卡里写明冲突。集中流动性池（`pool.exchange` 带 `_v3` / `_v4` / `clmm` / `dlmm`）本来就没有 LP 代币，本项判**不适用**。
