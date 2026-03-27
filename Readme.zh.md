<div align="center">

<img src="static/gmgnagentskills.png" alt="GMGN Agent Skills" />

[![X](https://img.shields.io/badge/关注-%40gmgnai-black?logo=x&logoColor=white)](https://x.com/gmgnai) [![Telegram](https://img.shields.io/badge/Telegram-gmgnagentapi-2CA5E0?logo=telegram&logoColor=white)](https://t.me/gmgnagentapi) [![Discord](https://img.shields.io/badge/Discord-gmgnai-5865F2?logo=discord&logoColor=white)](https://discord.gg/gmgnai)

[English](Readme.md) | 简体中文

</div>

## GMGN Agent Skills

使用 GMGN Agent Skills，你可以通过 AI Agent 实时查询多个链上热门代币排行榜，代币基础信息，社交媒体信息，实时交易动态，实时战壕新币，报持仓大户（Top Holder），交易大户（Top Trader），聪明钱持仓占比，KOL持仓占比，老鼠仓持仓，捆绑持仓占比，等代币专业数据分析数据，以及支持代币市价单交易、限价单交易、高级止盈止损策略单交易，以及钱包资产管理相关功能，例如查询钱包实时持仓、钱包最近盈亏、钱包交易动态等，全部通过自然语言与 AI Agent 交互即可完成。

---

## 技能

| 技能 | 说明 | 参考 |
|------|------|------|
| [`/gmgn-token`](skills/gmgn-token/SKILL.md) | Token 信息、安全、池子、持有者、交易者 | [SKILL.md](skills/gmgn-token/SKILL.md) |
| [`/gmgn-market`](skills/gmgn-market/SKILL.md) | K 线行情数据、热门代币 | [SKILL.md](skills/gmgn-market/SKILL.md) |
| [`/gmgn-portfolio`](skills/gmgn-portfolio/SKILL.md) | 钱包持仓、活动、统计 | [SKILL.md](skills/gmgn-portfolio/SKILL.md) |
| [`/gmgn-track`](skills/gmgn-track/SKILL.md) | 追踪关注钱包交易动态、KOL 交易动态、聪明钱交易动态 | [SKILL.md](skills/gmgn-track/SKILL.md) |
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | 兑换提交 + 订单查询 | [SKILL.md](skills/gmgn-swap/SKILL.md) |

> 如需查看详细的 CLI 接口说明、传参格式和推荐值，请参阅 [Wiki 文档](https://github.com/GMGNAI/gmgn-skills/wiki/Home-Chinese)。

### 快速开始安装

已准备好？[点击这里开始安装 Skills →](#开始安装-skills)

> **提示：** 如果你的 AI Agent 尝试直接打开 gmgn.ai 网站而不是使用 CLI，请在提示词中加上：
> ```
> 用 gmgn-cli 命令，不要直接请求gmgn.ai网页接口。
> ```

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

## 开始安装 Skills

安装前，请先在 **https://gmgn.ai/ai** 创建 API Key，用于：

1. 读取数据：代币、榜单、K 线、特色数据指标
2. 提交交易：市价立即交易、创建限价单、策略单等

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

### 方式一：通过 AI Agent 验证

发送以下提示词给你的 AI Agent：

```
执行这个cli命令：GMGN_API_KEY=gmgn_solbscbaseethmonadtron npx gmgn-cli market trending --chain sol --interval 1h --limit 3
```

### 方式二：通过 CLI 验证

使用公共 API Key 测试，无需注册：

```bash
GMGN_API_KEY=gmgn_solbscbaseethmonadtron npx gmgn-cli market trending --chain sol --interval 1h --limit 3
```

看到 JSON 输出即表示 CLI 正常工作。公共 Key 支持所有只读接口（token / market / portfolio），公共 Key 仅用于测试，正式使用任何接口均需申请个人 API Key（见第 3 步）。

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
3. 重启 Cline — `/gmgn-token`、`/gmgn-market`、`/gmgn-portfolio`、`/gmgn-track`、`/gmgn-swap` 即可使用

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

## 7. CLI 参考

完整参数说明：[docs/cli-usage.md](docs/cli-usage.md)。所有命令均支持 `--raw` 输出单行 JSON（方便 `jq` 等工具处理）。

### Token

```bash
# 基本信息 + 实时价格
npx gmgn-cli token info --chain sol --address <addr>

# 安全指标（蜜罐、税率、集中度、rug 风险）
npx gmgn-cli token security --chain sol --address <addr>

# 流动池信息（DEX、储备量、深度）
npx gmgn-cli token pool --chain sol --address <addr>

# 持仓大户（按持仓比例排序）
npx gmgn-cli token holders --chain sol --address <addr> --limit 50

# 聪明钱持仓大户（按买入量排序）
npx gmgn-cli token holders --chain sol --address <addr> \
  --tag smart_degen --order-by buy_volume_cur --limit 20

# 交易大户（KOL，按已实现盈利排序）
npx gmgn-cli token traders --chain sol --address <addr> \
  --tag renowned --order-by profit --limit 20
```

### Market

```bash
# K 线数据（1h 周期，最近 24 小时）
# macOS:
npx gmgn-cli market kline \
  --chain sol --address <addr> \
  --resolution 1h \
  --from $(date -v-24H +%s) --to $(date +%s)
# Linux: $(date -d '24 hours ago' +%s)

# 热门代币榜（SOL，1h，按交易量排序）
npx gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --order-by volume --limit 20 \
  --filter not_risk --filter not_honeypot

# 战壕新币列表
npx gmgn-cli market trenches \
  --chain sol \
  --type new_creation --type near_completion --type completed \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform letsbonk \
  --limit 80
```

### Portfolio

```bash
# 钱包持仓
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>

# 交易记录
npx gmgn-cli portfolio activity --chain sol --wallet <addr>

# 交易统计（支持多钱包）
npx gmgn-cli portfolio stats --chain sol --wallet <addr1> --wallet <addr2>

# API Key 绑定的钱包及主币余额
npx gmgn-cli portfolio info

# 单个 token 余额
npx gmgn-cli portfolio token-balance --chain sol --wallet <addr> --token <token_addr>
```

### Track

```bash
# 追踪关注钱包的交易动态（需要 GMGN_PRIVATE_KEY）
npx gmgn-cli track follow-wallet --chain sol
npx gmgn-cli track follow-wallet --chain sol --wallet <wallet_address> --side buy

# KOL 交易动态
npx gmgn-cli track kol --limit 100 --raw
npx gmgn-cli track kol --chain sol --side buy --limit 50 --raw

# 聪明钱交易动态
npx gmgn-cli track smartmoney --limit 100 --raw
npx gmgn-cli track smartmoney --chain sol --side sell --limit 50 --raw
```

### Swap（需要私钥）

```bash
# 提交兑换（固定滑点）
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --slippage 0.01

# 提交兑换（自动滑点）
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --auto-slippage

# 按持仓比例卖出（例：卖出 50%）
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <token-addr> \
  --output-token <usdc-addr> \
  --percent 50 \
  --auto-slippage

# 获取报价（不提交交易）
npx gmgn-cli order quote \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --slippage 0.01

# 查询订单状态
npx gmgn-cli order get --chain sol --order-id <order-id>
```

## 8. 支持的链

| 接口类型 | 支持的链 | 链原生货币 |
|----------|----------|-----------|
| token / market / portfolio / track | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL、USDC · bsc: BNB、USDC · base: ETH、USDC |

---

## 9. 升级 Skills 和 CLI

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

## 10. 安全与免责

**关于 `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` 是用于对 GMGN OpenAPI 请求进行签名认证的**签名密钥**，不是区块链钱包私钥，不直接控制链上资产。若泄露，攻击者可以伪造经过认证的 API 请求——请立即通过 GMGN 控制台轮换密钥。

**最佳实践**

- 限制配置文件权限：`chmod 600 ~/.config/gmgn/.env`
- 不要将 `.env` 文件提交到版本控制系统，请将其加入 `.gitignore`
- 不要在日志、截图或聊天中泄露 `GMGN_API_KEY` 或 `GMGN_PRIVATE_KEY`
- 请使用最新的 gmgn-cli（`npm install -g gmgn-cli`），查看当前版本请使用 `gmgn-cli --version`。

**免责声明**

使用本工具及根据其输出做出的任何财务决策，风险由用户自行承担。GMGN 对因凭证管理不当导致的任何交易损失、错误或未授权访问不承担责任。
