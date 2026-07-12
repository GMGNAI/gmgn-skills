[CmdletBinding()]
param(
    [ValidateSet('strict', 'exploratory')]
    [string]$Mode = 'strict',

    [ValidateRange(1, 100)]
    [int]$Limit = 25,

    [switch]$UseDemoKey,

    [string]$InspectAddress,

    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$script:ApiCallMeasurements = [System.Collections.Generic.List[object]]::new()

# This is a research-only workflow. It never calls swap, order, or cooking commands.
$repoRoot = Split-Path -Parent $PSScriptRoot
$cli = Join-Path $repoRoot 'dist\index.js'

if (-not (Test-Path -LiteralPath $cli)) {
    throw "GMGN CLI build not found at $cli. Run 'npm ci' and 'npm run build' in $repoRoot first."
}

if ($UseDemoKey) {
    # GMGN's documented public key is for read-only testing only.
    $env:GMGN_API_KEY = 'gmgn_solbscbaseethmonadtron'
}

if ([string]::IsNullOrWhiteSpace($env:GMGN_API_KEY)) {
    throw "Set GMGN_API_KEY or use -UseDemoKey for read-only testing. Do not put a trade-capable key in this script."
}

$criteria = if ($Mode -eq 'strict') {
    [ordered]@{
        min_liquidity_usd       = 25000
        min_holders             = 100
        min_smart_wallets       = 5
        max_dev_hold_rate       = 0.05
        max_top10_hold_rate     = 0.25
        max_rat_trader_rate     = 0.10
        max_bundler_trade_rate  = 0.10
        max_creator_token_count = 100
        max_non_pool_holder     = 0.10
    }
} else {
    # Exploratory mode is deliberately labelled as observation, not a buy signal.
    [ordered]@{
        min_liquidity_usd       = 4500
        min_holders             = 20
        min_smart_wallets       = 1
        max_dev_hold_rate       = 0.15
        max_top10_hold_rate     = 0.30
        max_rat_trader_rate     = 0.10
        max_bundler_trade_rate  = 0.20
        max_creator_token_count = 2000
        max_non_pool_holder     = 0.15
    }
}

function Get-Number {
    param($Value)
    if ($null -eq $Value -or $Value -eq '') { return 0.0 }
    return [double]$Value
}

function Invoke-GmgnJson {
    param([string[]]$Arguments)

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $raw = (& node $cli @Arguments --raw 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        $timer.Stop()
        $script:ApiCallMeasurements.Add([ordered]@{
            command     = "gmgn-cli $($Arguments -join ' ')"
            milliseconds = $timer.ElapsedMilliseconds
            exit_code   = $LASTEXITCODE
            response_bytes = [Text.Encoding]::UTF8.GetByteCount($raw)
        })
        throw "gmgn-cli failed: $raw"
    }
    $timer.Stop()
    $script:ApiCallMeasurements.Add([ordered]@{
        command        = "gmgn-cli $($Arguments -join ' ')"
        milliseconds   = $timer.ElapsedMilliseconds
        exit_code      = 0
        response_bytes = [Text.Encoding]::UTF8.GetByteCount($raw)
    })
    try {
        return $raw | ConvertFrom-Json
    } catch {
        throw "gmgn-cli returned invalid JSON: $raw"
    }
}

function Get-RejectionReasons {
    param($Token, $Thresholds)

    $reasons = [System.Collections.Generic.List[string]]::new()
    if ((Get-Number $Token.liquidity) -lt $Thresholds.min_liquidity_usd) { $reasons.Add('liquidity_below_minimum') }
    if ((Get-Number $Token.holder_count) -lt $Thresholds.min_holders) { $reasons.Add('holder_count_below_minimum') }
    if ((Get-Number $Token.smart_degen_count) -lt $Thresholds.min_smart_wallets) { $reasons.Add('smart_money_count_below_minimum') }
    if ((Get-Number $Token.dev_team_hold_rate) -gt $Thresholds.max_dev_hold_rate) { $reasons.Add('dev_hold_rate_above_maximum') }
    if ((Get-Number $Token.top_10_holder_rate) -gt $Thresholds.max_top10_hold_rate) { $reasons.Add('top10_concentration_above_maximum') }
    if ([bool]$Token.is_wash_trading) { $reasons.Add('wash_trading_flag') }
    if ((Get-Number $Token.rat_trader_amount_rate) -gt $Thresholds.max_rat_trader_rate) { $reasons.Add('rat_trader_rate_above_maximum') }
    if ((Get-Number $Token.bundler_trader_amount_rate) -gt $Thresholds.max_bundler_trade_rate) { $reasons.Add('bundler_trade_rate_above_maximum') }
    if ((Get-Number $Token.creator_created_count) -gt $Thresholds.max_creator_token_count) { $reasons.Add('creator_history_above_maximum') }
    return $reasons
}

function Get-NonPoolHolderSummary {
    param([string]$Address, $Thresholds)

    $response = Invoke-GmgnJson @('token', 'holders', '--chain', 'sol', '--address', $Address, '--limit', '50', '--order-by', 'amount_percentage', '--direction', 'desc')
    $wallets = @($response.list | Where-Object { $_.addr_type -eq 0 })
    $topFive = @($wallets | Select-Object -First 5)
    $topFiveShare = if ($topFive.Count) { [math]::Round((($topFive | Measure-Object -Property amount_percentage -Sum).Sum), 6) } else { 0 }
    $largest = if ($wallets.Count) { Get-Number $wallets[0].amount_percentage } else { 0 }
    $riskTags = @($topFive | ForEach-Object { $_.maker_token_tags + $_.tags } | Where-Object { $_ -in @('bundler', 'rat_trader', 'sandwich_bot') } | Select-Object -Unique)

    return [ordered]@{
        wallet_rows              = $wallets.Count
        largest_non_pool_share   = $largest
        top_five_non_pool_share  = $topFiveShare
        risk_tags_in_top_five    = $riskTags
        concentration_pass       = ($largest -le $Thresholds.max_non_pool_holder)
    }
}

# Stage 1: pull an actual, current set of launchpad tokens with GMGN's server-side safe preset.
$launches = Invoke-GmgnJson @('market', 'trenches', '--chain', 'sol', '--type', 'new_creation', '--filter-preset', 'safe', '--limit', $Limit)
$tokens = @($launches.new_creation)

$screened = foreach ($token in $tokens) {
    $reasons = @(Get-RejectionReasons $token $criteria)
    [ordered]@{
        address                 = $token.address
        symbol                  = $token.symbol
        name                    = $token.name
        liquidity_usd           = Get-Number $token.liquidity
        holder_count            = Get-Number $token.holder_count
        smart_money_count       = Get-Number $token.smart_degen_count
        dev_hold_rate           = Get-Number $token.dev_team_hold_rate
        top10_holder_rate       = Get-Number $token.top_10_holder_rate
        rat_trader_rate         = Get-Number $token.rat_trader_amount_rate
        bundler_trade_rate      = Get-Number $token.bundler_trader_amount_rate
        creator_token_count     = Get-Number $token.creator_created_count
        rejected_reasons        = $reasons
        passes_stage_one        = ($reasons.Count -eq 0)
    }
}

# Stage 2: only investigate stage-one survivors. This keeps API use low and avoids treating a
# server-side filter as due diligence.
$candidates = foreach ($entry in @($screened | Where-Object passes_stage_one)) {
    $security = Invoke-GmgnJson @('token', 'security', '--chain', 'sol', '--address', $entry.address)
    $holderSummary = Get-NonPoolHolderSummary $entry.address $criteria
    $stageTwoReasons = [System.Collections.Generic.List[string]]::new()
    if (-not $security.renounced_mint) { $stageTwoReasons.Add('mint_authority_not_renounced') }
    if (-not $security.renounced_freeze_account) { $stageTwoReasons.Add('freeze_authority_not_renounced') }
    if ((Get-Number $security.buy_tax) -gt 0 -or (Get-Number $security.sell_tax) -gt 0) { $stageTwoReasons.Add('nonzero_tax') }
    if (-not $holderSummary.concentration_pass) { $stageTwoReasons.Add('largest_non_pool_holder_above_maximum') }
    if ($holderSummary.risk_tags_in_top_five.Count -gt 0) { $stageTwoReasons.Add('risk_tag_in_top_five_holders') }

    [ordered]@{
        token                   = $entry
        security                = [ordered]@{
            mint_renounced      = [bool]$security.renounced_mint
            freeze_renounced    = [bool]$security.renounced_freeze_account
            buy_tax             = Get-Number $security.buy_tax
            sell_tax            = Get-Number $security.sell_tax
        }
        holder_analysis         = $holderSummary
        passes_stage_two        = ($stageTwoReasons.Count -eq 0)
        rejected_reasons        = @($stageTwoReasons)
        disposition             = if ($stageTwoReasons.Count -eq 0) { 'research_watchlist_only' } else { 'reject_or_monitor_only' }
    }
}

# Optional manual inspection is useful when the current launch feed is so fresh that no token has
# enough liquidity or holders to reach stage two. It does not change the screen's pass/fail result.
$manualInspection = $null
if ($InspectAddress) {
    $info = Invoke-GmgnJson @('token', 'info', '--chain', 'sol', '--address', $InspectAddress)
    $entry = [ordered]@{
        address       = $info.address
        symbol        = $info.symbol
        name          = $info.name
        liquidity_usd = Get-Number $info.liquidity
        holder_count  = Get-Number $info.holder_count
        source        = 'manual_inspection'
    }
    $security = Invoke-GmgnJson @('token', 'security', '--chain', 'sol', '--address', $entry.address)
    $holderSummary = Get-NonPoolHolderSummary $entry.address $criteria
    $stageTwoReasons = [System.Collections.Generic.List[string]]::new()
    if (-not $security.renounced_mint) { $stageTwoReasons.Add('mint_authority_not_renounced') }
    if (-not $security.renounced_freeze_account) { $stageTwoReasons.Add('freeze_authority_not_renounced') }
    if ((Get-Number $security.buy_tax) -gt 0 -or (Get-Number $security.sell_tax) -gt 0) { $stageTwoReasons.Add('nonzero_tax') }
    if (-not $holderSummary.concentration_pass) { $stageTwoReasons.Add('largest_non_pool_holder_above_maximum') }
    if ($holderSummary.risk_tags_in_top_five.Count -gt 0) { $stageTwoReasons.Add('risk_tag_in_top_five_holders') }

    $manualInspection = [ordered]@{
        token                   = $entry
        security                = [ordered]@{
            mint_renounced      = [bool]$security.renounced_mint
            freeze_renounced    = [bool]$security.renounced_freeze_account
            buy_tax             = Get-Number $security.buy_tax
            sell_tax            = Get-Number $security.sell_tax
        }
        holder_analysis         = $holderSummary
        passes_stage_two        = ($stageTwoReasons.Count -eq 0)
        rejected_reasons        = @($stageTwoReasons)
        disposition             = if ($stageTwoReasons.Count -eq 0) { 'research_watchlist_only' } else { 'reject_or_monitor_only' }
    }
}

$callTimes = @($script:ApiCallMeasurements | ForEach-Object { [double]$_['milliseconds'] })
$totalMilliseconds = if ($callTimes.Count) { [math]::Round((($callTimes | Measure-Object -Sum).Sum), 1) } else { 0 }
$averageMilliseconds = if ($callTimes.Count) { [math]::Round((($callTimes | Measure-Object -Average).Average), 1) } else { 0 }

$result = [ordered]@{
    generated_at_utc            = [DateTime]::UtcNow.ToString('o')
    chain                       = 'sol'
    mode                        = $Mode
    read_only                   = $true
    note                        = 'A pass means research watchlist only. This script never recommends or executes a trade.'
    criteria                    = $criteria
    stage_one                   = [ordered]@{
        launches_returned       = $tokens.Count
        passed                  = @($screened | Where-Object passes_stage_one).Count
        rejected                = @($screened | Where-Object { -not $_.passes_stage_one }).Count
        results                 = @($screened)
    }
    stage_two_candidates        = @($candidates)
    manual_inspection           = $manualInspection
    benchmark                   = [ordered]@{
        total_calls             = $script:ApiCallMeasurements.Count
        total_milliseconds      = $totalMilliseconds
        average_milliseconds    = $averageMilliseconds
        api_calls               = @($script:ApiCallMeasurements)
    }
}

$json = $result | ConvertTo-Json -Depth 8
if ($OutputPath) {
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
    $json | Set-Content -LiteralPath $resolved -Encoding utf8
    Write-Host "Wrote result to $resolved"
}

$json
