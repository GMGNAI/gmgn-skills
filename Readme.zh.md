<div align="center">

<img src="static/gmgnagentskills.png" alt="GMGN Agent Skills" />

[![X](https://img.shields.io/badge/关注-%40gmgnai-black?logo=x&logoColor=white)](https://x.com/gmgnai) [![Telegram](https://img.shields.io/badge/Telegram-gmgnagentapi-2CA5E0?logo=telegram&logoColor=white)](https://t.me/gmgnagentapi) [![Discord](https://img.shields.io/badge/Discord-gmgnai-5865F2?logo=discord&logoColor=white)](https://discord.gg/gmgnai)

[English](Readme.md) | 简体中文

</div>

## GMGN Agent Skills

使用 GMGN Agent Skills，你可以通过 AI Agent 实时查询多个链上热门代币排行榜，代币基础信息，社交媒体信息，实时交易动态，实时战壕新币，报持仓大户（Top Holder），交易大户（Top Trader），聪明钱持仓占比，KOL持仓占比，老鼠仓持仓，捆绑持仓占比，等代币专业数据分析数据，以及支持代币市价单交易、限价单交易、高级止盈止损策略单交易、一键 Cooking 策略单（买入 + 条件单一体化），以及钱包资产管理相关功能，例如查询钱包实时持仓、钱包最近盈亏、钱包交易动态等，全部通过自然语言与 AI Agent 交互即可完成。

---

## 为什么选择 GMGN Skills

> 专为 AI Agent 高速实时查询、交易多链 Meme 代币而生。GMGN Skills 让 AI Agent 可以实时批量查询 GMGN 网站展示的热门代币、Trenches新创建代币，以及聪明钱、KOL、老鼠仓等专业顶级交易数据。
>
> 凭借 500+ 专业数据分析维度，你可以将自己的 AI Agent 打造成 7×24 小时全天候托管的实时扫链交易工具——实时监控多链代币热点、实时下单、实时止盈止损，实现全自动化交易。

### 1. 链上实时数据查询快

SOL / BSC / Base / ETH 多链数据每次查询均为实时，支持多参数个性化调用，无快照缓存，方便AI Agent实时决策（包括不限于下表）。

| 数据类型 | 粒度 |
|---------|------|
| 新币发现（战壕） | 实时，按 Launchpad 平台，dev持仓，KOL持仓，老鼠仓持仓分类 |
| 热门代币榜单 | 实时，`1m` / `5m` / `1h` / `6h` / `24h`，最低支持 **1 分钟**窗口 |
| 代币信息 |实时，交易动态 / 代币价格 / 交易量 / 市值 等|
|代币安全 |实时，是否开源，弃权，貔貅检测等 |
|代币数据分析|实时，Dev / KOL / 聪明钱 / 老鼠仓 / 捆绑钱包等持仓占比 等|
|监控追踪|实时，KOL / 聪明钱 / 关注的钱包交易动态 / 天眼信号(开发中) 等|
| K 线（OHLCV） | 实时，`1m` / `5m` / `15m` / `1h` / `4h` / `1d`，最低支持 **1 分钟** |
|资产持仓|实时，持仓/盈亏/交易动态 等|




### 2. 交易更快

- 与 GMGN 网页端共享同一套 RPC 路由，多区域部署，毫秒级响应，从下单到上链延时小于 **0.3 秒**。
- 交易自动找最佳路由，与 GMGN 网页端同一套
- 单条命令支持市价单、限价单、策略单（止盈 / 止损）。
- 支持按仓位比例卖出（`--percent 50`），无需手动计算数量。

| 订单类型 | 说明 |
|----------|------|
| 市价单 | 以当前市价即时成交 |
| 限价单 | 设定触发价格，到价买入或卖出 |
| 止盈 / 止损 | 随买单附带固定价格的退出条件 |
| 追踪止盈 / 追踪止损 | 跟踪价格峰值，回撤达到指定比例后触发，吃满行情同时保护收益 |
| 多钱包批量交易 | 多个钱包同时买入，每个钱包分别创建对应的止盈 / 止损 / 追踪止盈 / 追踪止损订单 |

### 3. 特色数据更全

不用再爬网页，不会被Claudeflare拦截，现在就可以快速/多并发实时查询多链的 Meme 代币高频交易所需的所有专业分析指标数据 (包括不限于)：

- **聪明钱数量**（`smart_degen_count`）和 **KOL 持仓**（`renowned_wallets`）— 实时
- **老鼠仓占比**（`rat_trader_amount_rate`）— 内幕 / 偷跑钱包的交易量份额
- **捆绑钱包暴露度**（`bundler_trader_amount_rate`）— 机器人捆绑买入的交易量占比
- **狙击钱包数**（`sniper_count`）— 在代币刚开盘瞬间买入的钱包数量
- **疑似内幕持仓比**（`suspected_insider_hold_rate`）
- **新钱包占比**（`fresh_wallet_rate`）
- **Rug 风险评分**（0–1）+ 貔貅检测 + 对倒洗盘识别
- **Bonding Curve 状态**（`is_on_curve`）— 代币是否已毕业到开放 DEX

### 4. 可以用 GMGN Skills 做什么

**实时查链**
- 扫描战壕新币，按 Launchpad（Pump.fun、letsbonk、fourmeme、clanker……）、dev 持仓、KOL 进场、老鼠仓占比实时过滤
- 浏览多链热门代币榜单（最低 1 分钟粒度），按交易量、聪明钱数量、市值等多维排序
- 实时追踪新币，追踪KOL/聪明/已关注的钱包最近在买哪些新币，自动分析最新热门代币
- 获取任意代币的实时 K 线 / OHLCV 数据（1m / 5m / 15m / 1h / 4h / 1d）

**代币数据分析**
- 查询代币基础信息、社交链接、Bonding Curve 状态、流动性池详情
- 安全核查：是否开源、弃权、貔貅、对倒洗盘、Rug 风险评分（0–1）
- 深度持仓分析：聪明钱 / KOL / 老鼠仓 / 捆绑钱包 / 狙击手 / 巨鲸 / 新钱包 各类持仓占比及排名

**钱包与追踪**
- 分析任意钱包：实时持仓、已实现 / 未实现盈亏、胜率、交易风格、历史流水
- 实时追踪聪明钱、KOL 和关注钱包的最新买卖动态

**自动化交易**
- 市价单、限价单、止盈止损策略单，从下单到上链延时 < 0.3 秒
- 按仓位比例一键卖出（`--percent 50`），无需手动计算数量

**AI 工作流**
- 9 个内置工作流文档：代币研究、项目深度报告、钱包分析、聪明钱画像、风险预警、早期项目筛选、每日简报、市场发现等，开箱即用

---

## 技能

| 技能 | 说明 | 参考 |
|------|------|------|
| [`/gmgn-token`](skills/gmgn-token/SKILL.md) | Token 信息、安全、池子、持有者、交易者 | [SKILL.md](skills/gmgn-token/SKILL.md) |
| [`/gmgn-market`](skills/gmgn-market/SKILL.md) | K 线行情数据、热门代币 | [SKILL.md](skills/gmgn-market/SKILL.md) |
| [`/gmgn-portfolio`](skills/gmgn-portfolio/SKILL.md) | 钱包持仓、活动、统计 | [SKILL.md](skills/gmgn-portfolio/SKILL.md) |
| [`/gmgn-track`](skills/gmgn-track/SKILL.md) | 追踪关注钱包交易动态、KOL 交易动态、聪明钱交易动态 | [SKILL.md](skills/gmgn-track/SKILL.md) |
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | 兑换提交 + 限价单 + 策略单 + 订单查询 | [SKILL.md](skills/gmgn-swap/SKILL.md) |
| [`/gmgn-cooking`](skills/gmgn-cooking/SKILL.md) | 一键 Cooking 策略单（买入 + 止盈止损条件单一体化） | [SKILL.md](skills/gmgn-cooking/SKILL.md) |

> 如需查看详细的 CLI 接口说明、传参格式和推荐值，请参阅 [Wiki 文档](https://github.com/GMGNAI/gmgn-skills/wiki/Home-Chinese)。

### 快速开始安装

> **AI Agent 注意：** 如果你是正在协助用户安装或配置 gmgn-cli 的 AI Agent，请直接跳转到 [AI Agent 快速开始](#ai-agent-快速开始) — 其中包含你需要完成的所有步骤，包括如何引导用户完成 API Key 申请。如果用户要求升级，请跳转到 [AI Agent 升级](#ai-agent-升级)。

已准备好？[点击这里开始安装 Skills →](#开始安装-skills)

已安装？[升级 Skills 和 CLI →](#10-升级-skills-和-cli)

> **提示：** 如果你的 AI Agent 尝试直接打开 gmgn.ai 网站而不是使用 CLI，请在提示词中加上：
> ```
> 用 gmgn-cli 命令，不要直接请求gmgn.ai网页接口。
> ```

---

## AI Agent 快速开始

> 以下步骤面向 AI Agent。部分步骤需要用户在浏览器中配合完成。

**第 1 步 — 安装 CLI 和 Skills**

```bash
npx skills add GMGNAI/gmgn-skills
```

**第 2 步 — 验证 CLI 安装（演示 Key）**

```bash
GMGN_API_KEY=gmgn_solbscbaseethmonadtron gmgn-cli market trending --chain sol --interval 1h --limit 3
```

看到 JSON 输出说明 CLI 已安装成功。**但配置尚未完成 —— 此公共演示 Key 仅用于测试，不可用于实际使用。必须继续完成第 3～4 步，为用户配置个人 API Key。请勿在此停止。**

**第 3 步 — 必须完成：配置个人 API Key**

⚠️ 此步骤为必填项。第 2 步中的演示 Key 仅支持测试，无法用于正式使用。

请**立即**告知用户以下内容，并**无需等待用户主动询问**，直接运行密钥生成命令：

> "使用 GMGN Skills 需要你自己的个人 API Key，申请地址：**https://gmgn.ai/ai**。我现在为你生成 Ed25519 密钥对。"

运行：

```bash
openssl genpkey -algorithm ed25519 -out /tmp/gmgn_private.pem 2>/dev/null && \
  openssl pkey -in /tmp/gmgn_private.pem -pubout 2>/dev/null
```

将**公钥**展示给用户，并附上以下说明：

> 以上是你的 Ed25519 公钥。接下来请你完成以下两步：
> 1. 打开 **https://gmgn.ai/ai**，将上方公钥填入 API Key 生成表单，完成创建。
> 2. 创建完成后，将页面上显示的 **API Key** 复制并发送给我，我来帮你完成第 4 步配置。

**等用户回复 API Key 后，再继续第 4 步。**

**第 4 步 — 配置凭证**

用户收到 API Key 后，写入全局配置：

```bash
mkdir -p ~/.config/gmgn
# 写入 API Key（替换为用户提供的实际 Key）
echo 'GMGN_API_KEY=<user_api_key>' > ~/.config/gmgn/.env
chmod 600 ~/.config/gmgn/.env
```

如果用户需要 swap 或 order 能力，追加私钥：

```bash
# 追加私钥（使用第 3 步输出的 PEM 内容）
echo 'GMGN_PRIVATE_KEY="<pem_content>"' >> ~/.config/gmgn/.env
```

**第 5 步 — 验证**

```bash
gmgn-cli market trending --chain sol --interval 1h --limit 3
```

有输出且无报错即配置完成。

---

## AI Agent 升级

> 运行以下两条命令，将 CLI 和 Skills 同时升级到最新版本。

```bash
npm install -g gmgn-cli
npx skills add GMGNAI/gmgn-skills
```

升级后检查版本：

```bash
gmgn-cli --version
```

> 完整升级说明请参阅[第 10 节 — 升级 Skills 和 CLI](#10-升级-skills-和-cli)。

---

## 使用案例

### 查询热门代币榜

发送下面提示词给 AI Agent：

```
查 Solana 1h 热门榜，筛出 6 小时内创建的新币，并且platforms是pump.fun的代币，然后按交易量从高到低排列。
```

![查询热门代币榜](static/market-rank-1h-Pumpfun-cn.png)

### 实时分析代币交易走势

发送下面提示词给 AI Agent：

```
查看第一个代币的 K 线，分析入场时机，并提供社交媒体链接以及聪明资金 / KOL 的交易分析。
```

![代币分析 1](static/market-tokenanalysis-cn01.png)
![代币分析 2](static/market-tokenanalysis-cn02.png)

---

## 1. 安装

选择以下任意一种方式

### 1.1 通过 Agent 安装（推荐）

发送给你的 AI Agent：

```bash
npx skills add GMGNAI/gmgn-skills
```

### 1.2 npm 全局安装

```bash
npm install -g gmgn-cli
```

### 1.3 本地开发

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

## 2. 验证连通性

使用公共 API Key 测试，无需注册：

```bash
GMGN_API_KEY=gmgn_solbscbaseethmonadtron gmgn-cli market trending --chain sol --interval 1h --limit 3
```

看到 JSON 输出即表示 CLI 正常工作。公共 Key 支持所有只读接口（token / market / portfolio），公共 Key 仅用于测试，正式使用任何接口均需申请个人 API Key（见第 3 步）。

> **排查 401 / 403 错误：** 如果命令返回 `401` 或 `403` 且凭证看起来正确，出口请求可能走了 IPv6（GMGN API 不支持）。立即排查：(1) 运行 `ifconfig | grep inet6`（macOS）或 `ip addr show | grep inet6`（Linux）列出所有网络接口及其 IPv6 地址；(2) 运行 `curl -s https://ipv6.icanhazip.com`——如果返回 IPv6 地址，说明流量走了 IPv6。**请立即关闭 IPv6，gmgn-cli 命令只能通过 IPv4 请求。**

## 3. 申请个人 API Key

第 2 步的公共 Key 仅用于测试。正式使用（只读接口和 swap）均需在 https://gmgn.ai/ai 申请个人 API Key，需要准备：

### 3.1 生成 Ed25519 密钥对

**方式一：输入提示词（推荐）**

将以下提示词发送给你的 AI Agent：

```
帮我用 OpenSSL 生成一个 Ed25519 密钥对，并分别显示给我：
1. 公钥（我需要填写到GMGN网站上的 API Key 创建表单中）
2. PEM 格式的私钥（我需要将它设置为 .env 中的 GMGN_PRIVATE_KEY）
```

**方式二：Binance Key Generator**

下载并运行 [Binance Asymmetric Key Generator](https://github.com/binance/asymmetric-key-generator/releases)。

申请时填入**公钥**。

### 3.2 获取本机出口 IP

用于填写 IP 白名单（开通 API Key 的交易能力时需要）：

```bash
curl ip.me
```

## 4. 配置个人 API Key

### 方式一：全局配置（推荐）

创建 `~/.config/gmgn/.env`，配置一次，所有目录均生效：

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here

# 仅 swap / order 接口需要：
GMGN_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n"
EOF
```

### 方式二：项目 `.env`

```bash
cp .env.example .env
# 编辑 .env，填入实际值
```

配置加载顺序：`~/.config/gmgn/.env` → 项目 `.env`（项目级优先）。

## 5. 在 AI 客户端中使用

#### OpenClaw

直接发送以下提示词，测试查询能力：

```
查询 Solana 链 1 小时热门代币
```

#### Claude Code

安装包后通过插件机制自动发现技能。

#### Cursor

技能通过 `.cursor-plugin/` 配置自动发现。

1. 完成上方安装和配置步骤
2. 重启 Cursor — Agent 模式下可通过 `/gmgn-*` 命令使用技能

#### Cline

1. 完成上方安装和配置步骤
2. 在 Cline 设置 → **Skills directory**：填入已安装包的 `skills/` 目录路径：
   ```bash
   echo "$(npm root -g)/gmgn-skills/skills"
   ```
3. 重启 Cline — `/gmgn-token`、`/gmgn-market`、`/gmgn-portfolio`、`/gmgn-track`、`/gmgn-swap`、`/gmgn-cooking` 即可使用

#### Codex CLI

```bash
git clone https://github.com/GMGNAI/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.codex/INSTALL.md](.codex/INSTALL.md)

#### OpenCode

```bash
git clone https://github.com/GMGNAI/gmgn-skills ~/.opencode/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.opencode/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.opencode/INSTALL.md](.opencode/INSTALL.md)

---

## 6. 使用示例

### 常用指令

安装技能后，向 AI 助手直接发送自然语言指令：

```
用 0.1 SOL 买入 <token_address>
卖出 BSC 上 <token_address> 的 50%
把我持有的 <token_address> 卖掉 30%
查询报价，我想用 1 SOL 换 <token_address>，能换多少
查询订单状态 <order_id>
solana 上的 <token_address> 安全吗，值得买入吗？
查看 <token_address> 的前十大持有者
查看 <token_address> 的聪明钱持仓，按买入量排序
查看 <token_address> 最近的 KOL 交易动态
查看我在 SOL 上的钱包持仓
查询 0x1234... 的代币详情
查看 <token_address> 过去 24 小时的 K 线和交易量
查看 BSC 上钱包 <wallet_address> 的交易统计
查看钱包 <wallet_address> 最近的交易记录
我的 API Key 绑定了哪些钱包，余额各是多少
查看 SOL 链上最新的聪明钱交易动态
查看 SOL 链上 KOL 最近在买什么
查询 Solana 上最新发布的代币
查询 Solana 1 分钟交易热门代币
```

### 典型使用场景

**研究 Token：**
```
查询代币信息  →  查询安全指标  →  查询流动池  →  查询持有者
```

**分析钱包：**
```
查询钱包持仓  →  查询交易统计  →  查询交易记录
```

**执行交易：**
```
确认代币信息  →  检查余额  →  提交兑换  →  轮询订单状态
```

**通过热门榜单发现交易机会：**
```
获取热门代币（50 条）  →  AI 多维度分析选出 top 5  →  用户确认  →  查询代币信息 / 安全指标  →  提交兑换
```

---

## 7. 工作流文档

常用分析任务的分步指引：

| 工作流 | 适用场景 |
|--------|---------|
| [workflow-token-research.md](docs/workflow-token-research.md) | 买入前 Token 尽调（地址 → 买入/观望/跳过） |
| [workflow-project-deep-report.md](docs/workflow-project-deep-report.md) | 多维度评分的深度项目报告 |
| [workflow-wallet-analysis.md](docs/workflow-wallet-analysis.md) | 钱包质量评估（地址 → 是否值得跟随） |
| [workflow-smart-money-profile.md](docs/workflow-smart-money-profile.md) | 聪明钱行为画像、跟单收益估算、排行榜对比 |
| [workflow-risk-warning.md](docs/workflow-risk-warning.md) | 持仓风险预警（巨鲸出货、流动性、开发者跑路） |
| [workflow-early-project-screening.md](docs/workflow-early-project-screening.md) | 筛选新发 Launchpad Token，识别聪明钱早入信号 |
| [workflow-daily-brief.md](docs/workflow-daily-brief.md) | 每日市场简报：热门趋势 + 聪明钱动向 + 早期机会 + 风险扫描 |
| [workflow-market-opportunities.md](docs/workflow-market-opportunities.md) | 从趋势数据中发现交易机会 |
| [workflow-token-due-diligence.md](docs/workflow-token-due-diligence.md) | 4 步 Token 尽调清单 |

## 8. CLI 参考

完整参数说明：[docs/cli-usage.md](docs/cli-usage.md)。所有命令均支持 `--raw` 输出单行 JSON（方便 `jq` 等工具处理）。

### Token
```bash
# 基本信息 + 实时价格
gmgn-cli token info --chain sol --address <addr>

# 安全指标（蜜罐、税率、集中度、rug 风险）
gmgn-cli token security --chain sol --address <addr>

# 流动池信息（DEX、储备量、深度）
gmgn-cli token pool --chain sol --address <addr>

# 持仓大户（按持仓比例排序）
gmgn-cli token holders --chain sol --address <addr> --limit 50

# 聪明钱持仓大户（按买入量排序）
gmgn-cli token holders --chain sol --address <addr> \
  --tag smart_degen --order-by buy_volume_cur --limit 20

# 交易大户（KOL，按已实现盈利排序）
gmgn-cli token traders --chain sol --address <addr> \
  --tag renowned --order-by profit --limit 20
```

### Market

```bash
# K 线数据（1h 周期，最近 24 小时）
# macOS:
gmgn-cli market kline \
  --chain sol --address <addr> \
  --resolution 1h \
  --from $(date -v-24H +%s) --to $(date +%s)
# Linux: $(date -d '24 hours ago' +%s)

# 热门代币榜（SOL，1h，按交易量排序）
gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --order-by volume --limit 20 \
  --filter not_risk --filter not_honeypot

# 战壕新币列表
gmgn-cli market trenches \
  --chain sol \
  --type new_creation --type near_completion --type completed \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform letsbonk \
  --limit 80

# 服务端过滤：安全预设 + 要求有聪明钱 + 按聪明钱数量排序
gmgn-cli market trenches \
  --chain sol --type new_creation \
  --filter-preset safe --min-smart-degen-count 1 --sort-by smart_degen_count
```

### Portfolio

```bash
# 钱包持仓
gmgn-cli portfolio holdings --chain sol --wallet <addr>

# 交易记录
gmgn-cli portfolio activity --chain sol --wallet <addr>

# 交易统计（支持多钱包）
gmgn-cli portfolio stats --chain sol --wallet <addr1> --wallet <addr2>

# API Key 绑定的钱包及主币余额
gmgn-cli portfolio info

# 单个 token 余额
gmgn-cli portfolio token-balance --chain sol --wallet <addr> --token <token_addr>

# 查询开发者钱包创建的代币列表
gmgn-cli portfolio created-tokens --chain sol --wallet <addr>
```

### Track

```bash
# 追踪关注钱包的交易动态
gmgn-cli track follow-wallet --chain sol
gmgn-cli track follow-wallet --chain sol --limit 20 --min-amount-usd 1000

# KOL 交易动态
gmgn-cli track kol --limit 100 --raw
gmgn-cli track kol --chain sol --side buy --limit 50 --raw

# 聪明钱交易动态
gmgn-cli track smartmoney --limit 100 --raw
gmgn-cli track smartmoney --chain sol --side sell --limit 50 --raw
```

### Swap / Quote / Query

```bash
# 提交兑换（固定滑点）
gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --slippage 0.01

# 提交兑换（自动滑点）
gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --auto-slippage

# 按持仓比例卖出（例：卖出 50%）
gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <token-addr> \
  --output-token <usdc-addr> \
  --percent 50 \
  --auto-slippage

# 获取报价（不提交交易）
gmgn-cli order quote \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --slippage 0.01

# 所有链上的 quote 都走关键鉴权，需要 GMGN_PRIVATE_KEY
gmgn-cli order quote \
  --chain bsc \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000000000000000 \
  --slippage 0.01

# 查询订单状态
gmgn-cli order get --chain sol --order-id <order-id>

# 多钱包并发 Swap
gmgn-cli multi-swap \
  --chain sol \
  --accounts <addr1>,<addr2> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --input-amount '{"<addr1>":"1000000","<addr2>":"2000000"}' \
  --slippage 0.01
```

> `order quote` 在 `sol` / `bsc` / `base` / `eth` 上都走关键鉴权，必须配置 `GMGN_PRIVATE_KEY`。

### 带止盈止损的 Swap（需要私钥）

**`hold_amount` 模式** — 按触发时的实际持仓比例卖出：

```bash
# 用 0.01 SOL 买入代币 A；涨 100% 卖 50%，涨 300% 卖剩余 50%，跌 65% 全卖
gmgn-cli swap \
  --chain sol \
  --from <wallet_address> \
  --input-token So11111111111111111111111111111111111111112 \
  --output-token <token_A_address> \
  --amount 10000000 \
  --slippage 0.3 \
  --anti-mev \
  --condition-orders '[{"order_type":"profit_stop","side":"sell","price_scale":"100","sell_ratio":"50"},{"order_type":"profit_stop","side":"sell","price_scale":"300","sell_ratio":"100"},{"order_type":"loss_stop","side":"sell","price_scale":"65","sell_ratio":"100"}]' \
  --sell-ratio-type hold_amount
```

> `price_scale` 止盈时为涨幅百分比（`"100"` = 涨 100% / 2×，`"300"` = 涨 300% / 4×）；止损时为跌幅百分比（`"65"` = 跌 65%，触发价为入场价的 35%）。
> `hold_amount`：第二个止盈单触发时，按触发时持仓（剩余 50%）的 100% 卖出。如果中间有加仓，加仓的部分也会一同被卖掉。

**`buy_amount` 模式** — 按原始买入量的固定百分比卖出：

```bash
# 相同策略，使用原始买入量的固定百分比
gmgn-cli swap \
  --chain sol \
  --from <wallet_address> \
  --input-token So11111111111111111111111111111111111111112 \
  --output-token <token_A_address> \
  --amount 10000000 \
  --slippage 0.3 \
  --anti-mev \
  --condition-orders '[{"order_type":"profit_stop","side":"sell","price_scale":"100","sell_ratio":"50"},{"order_type":"profit_stop","side":"sell","price_scale":"300","sell_ratio":"50"},{"order_type":"loss_stop","side":"sell","price_scale":"65","sell_ratio":"100"}]' \
  --sell-ratio-type buy_amount
```

> `buy_amount`：每个止盈单各卖原始买入量的 50%，止损单卖原始买入量的 100%。

---

### 限价单（需要私钥）

```bash
# 创建止盈单
gmgn-cli order strategy create \
  --chain sol \
  --from <wallet_address> \
  --base-token <token_address> \
  --quote-token <sol_address> \
  --sub-order-type take_profit \
  --check-price 0.002 \
  --amount-in-percent 100 \
  --slippage 0.01

# 创建止损单
gmgn-cli order strategy create \
  --chain sol \
  --from <wallet_address> \
  --base-token <token_address> \
  --quote-token <sol_address> \
  --sub-order-type stop_loss \
  --check-price 0.0005 \
  --amount-in-percent 100 \
  --slippage 0.01

# 查看当前挂单（需要私钥）
gmgn-cli order strategy list --chain sol

# 撤销策略单
gmgn-cli order strategy cancel --chain sol --from <wallet_address> --order-id <order_id>
```

### Cooking 一键策略单（需要私钥）

```bash
# 买入代币，同时自动挂止盈 + 止损条件单
gmgn-cli cooking \
  --chain sol \
  --from <wallet_address> \
  --input-token So11111111111111111111111111111111111111112 \
  --output-token <token_address> \
  --amount 1000000000 \
  --slippage 0.3 \
  --condition-orders '[{"order_type":"profit_stop","side":"sell","price_scale":"100","sell_ratio":"100"},{"order_type":"loss_stop","side":"sell","price_scale":"50","sell_ratio":"100"}]'
```

## 9. 支持的链

| 接口类型 | 支持的链 | 链原生货币 |
|----------|----------|-----------|
| token / market / portfolio / track | `sol` / `bsc` / `base` / `eth` | — |
| swap / order | `sol` / `bsc` / `base` / `eth` | sol: SOL、USDC · bsc: BNB、USDC · base: ETH、USDC · eth: ETH、USDC |

---

## 10. 升级 Skills 和 CLI

将 `gmgn-cli` 和 Skills 升级到最新版本：

**方式一：通过 AI Agent（推荐）**

发送给你的 AI Agent：

```
运行以下两条命令，更新 gmgn-cli 和 Skills 文档：
1. npm install -g gmgn-cli
2. npx skills add GMGNAI/gmgn-skills
```

**方式二：通过 CLI**

```bash
# 升级 gmgn-cli
npm install -g gmgn-cli

# 升级 Skills
npx skills add GMGNAI/gmgn-skills
```

**查看当前版本号**

```bash
gmgn-cli --version
```

---

## 11. 安全与免责（使用前必读）

本工具可供 AI Agent 调用以自动执行链上交易，存在模型幻觉、执行不可控、提示词注入等固有风险。AI Agent 在获得授权后，将以您绑定的钱包地址提交真实的链上交易，**交易一经上链即不可撤销**，可能导致资金损失，请您谨慎使用。

**关于 `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` 是用于对 GMGN OpenAPI 请求进行签名认证的**签名密钥**，不是区块链钱包私钥，不直接控制链上资产。若泄露，攻击者可以伪造经过认证的 API 请求——请立即通过 GMGN 控制台轮换密钥。

**最佳实践**

- 限制配置文件权限：`chmod 600 ~/.config/gmgn/.env`
- 不要将 `.env` 文件提交到版本控制系统，请将其加入 `.gitignore`
- 不要在日志、截图或聊天中泄露 `GMGN_API_KEY` 或 `GMGN_PRIVATE_KEY`
- 每次 swap 前，仔细核对 AI 呈现的交易摘要（链、钱包、代币地址、金额），确认无误后再回复确认
- 建议先用小额资金验证配置后再进行大额操作
- 请使用最新的 gmgn-cli（`npm install -g gmgn-cli`），查看当前版本请使用 `gmgn-cli --version`

**免责声明**

使用本工具及根据其输出做出的任何财务决策，风险由用户自行承担。GMGN 对因模型幻觉、提示词注入、凭证管理不当或用户操作失误导致的任何交易损失、错误或未授权访问不承担责任。使用本工具即视为您已充分知悉上述风险并自愿承担全部责任。
