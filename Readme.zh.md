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
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | 兑换提交 + 订单查询 | [SKILL.md](skills/gmgn-swap/SKILL.md) |

> 如需查看详细的 CLI 接口说明、传参格式和推荐值，请参阅 [Wiki 文档](https://github.com/GMGNAI/gmgn-skills/wiki/Home-Chinese)。

### 快速开始安装

已准备好？[点击这里开始安装 Skills →](#开始安装-skills)

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

选择以下任意一种方式：

### 1.1 通过 Agent 安装（推荐）

发送给你的 AI Agent：

```bash
npx skills add GMGNAI/gmgn-skills
```

### 1.2 npm 全局安装

```bash
npm install -g gmgn-cli@1.1.0
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
3. 重启 Cline — `/gmgn-token`、`/gmgn-market`、`/gmgn-portfolio`、`/gmgn-swap` 即可使用

#### Codex CLI

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

详细说明：[.codex/INSTALL.md](.codex/INSTALL.md)

#### OpenCode

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.opencode/gmgn-cli
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
查询订单状态 <order_id>
solana 上的 <token_address> 安全吗，值得买入吗？
查看 <token_address> 的前十大持有者
查看我在 SOL 上的钱包持仓
查询 0x1234... 的代币详情
查看 BSC 上钱包 <wallet_address> 的交易统计
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
npx gmgn-cli token info --chain sol --address <addr>
```

### Market

```bash
npx gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --order-by volume --limit 20 \
  --filter not_risk --filter not_honeypot
```

### Portfolio

```bash
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>
```

### Swap（需要私钥）

```bash
# 提交兑换
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --auto-slippage \
  --slippage 0.01

# 查询订单
npx gmgn-cli order get --chain sol --order-id <order-id>
```

## 8. 支持的链

| 接口类型 | 支持的链 | 链原生货币 |
|----------|----------|-----------|
| token / market / portfolio | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL、USDC · bsc: BNB、USDC · base: ETH、USDC |

---

## 9. 安全与免责

**关于 `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` 是用于对 GMGN OpenAPI 请求进行签名认证的**签名密钥**，不是区块链钱包私钥，不直接控制链上资产。若泄露，攻击者可以伪造经过认证的 API 请求——请立即通过 GMGN 控制台轮换密钥。

**最佳实践**

- 限制配置文件权限：`chmod 600 ~/.config/gmgn/.env`
- 不要将 `.env` 文件提交到版本控制系统，请将其加入 `.gitignore`
- 不要在日志、截图或聊天中泄露 `GMGN_API_KEY` 或 `GMGN_PRIVATE_KEY`
- 使用固定版本安装（`npm install -g gmgn-cli@1.1.0`），而非 `npx gmgn-cli`，以避免在持有凭证的环境中执行未预期的包更新

**免责声明**

使用本工具及根据其输出做出的任何财务决策，风险由用户自行承担。GMGN 对因凭证管理不当导致的任何交易损失、错误或未授权访问不承担责任。
