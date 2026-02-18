# Compare With Pro

Compare a player's game against a professional/high-rated player's game with the same civilization and strategy, identifying pattern differences and generating improvement suggestions.

## Inputs

- **Game URL**: $ARGUMENTS
  - AoE4 World game URL for the player's game (required)
  - Optional flag `--pro <name>`: specific pro to compare against (e.g., `--pro 燕子宇`, `--pro loueMT`)

**⚠️ 重要规则：**
- 如果用户只给了 profile URL，先查询最新游戏
- 如果无法自动获取 sig（curl 找不到），**必须问用户要完整 URL**
- **永远不要假设**用户的 match history 不公开
- **永远不要跳过**到旧游戏

## Available Pro Reference Data

Pre-scraped games with sigs from players with public match history:

| Player | Profile ID | Rating | Civs | English Games |
|--------|-----------|--------|------|---------------|
| EL.loueMT | 8354416 | 2366 | Ayyubids, Rus | 1 |
| 燕子宇 | 11018483 | 2242 | Chinese, English | 18 |

**Reference file:** `reference_data/english_pro_games.json`

```bash
# View available pro games
cat reference_data/english_pro_games.json | python3 -m json.tool | head -50
```

## Helper Script

`scripts/fetch_game_data.py` handles all data fetching:

```bash
# Compare both players' build orders from YOUR game (includes opponent data)
python3 scripts/fetch_game_data.py --url "<your_game_url>" --compare

# Fetch a pro's game summary
python3 scripts/fetch_game_data.py --url "<pro_game_url_with_sig>" --json
```

## Steps

### 0. 确认游戏 URL（必须）

**如果用户给了完整游戏 URL（带 sig）**：直接用。

**如果用户只给了 profile URL 或没给 URL**：
1. 查询最新游戏：`curl "https://aoe4world.com/api/v0/players/{id}/games?limit=1"`
2. 尝试从 games 页面抓 sig
3. **如果抓不到 → 停止，问用户**：
   > "我找到了你最新的游戏 (Game {id})，但需要带 sig 的完整 URL 才能获取详细数据。请在 aoe4world 上点开这局游戏，把完整 URL（包含 ?sig=xxx）发给我。"

**❌ 禁止行为**：
- 禁止假设用户的 match history 不公开
- 禁止跳到旧游戏
- 禁止在没有 sig 的情况下继续分析

### 1. Parse Player's Game

Extract profile_id, game_id, sig from the URL. Fetch the player's game data:

```bash
python3 scripts/fetch_game_data.py --url "<player_game_url>" --compare --json > /tmp/player_game.json
```

Identify:
- **Civilization** played
- **Rating** at time of game
- **Result** (win/loss)
- **Map**
- **Duration**

### 2. Find Reference Games (Multiple)

**Fetch multiple Pro games for statistical comparison:**

1. Load `reference_data/english_pro_games.json`
2. Filter by:
   - Same civilization
   - Preferably **wins** (shows good execution)
   - **Top 3-5 games** by rating or most recent

**If `--pro` specified:**
Use that player's games only.

**If no pro specified (auto-select):**
Use all available games from the reference file.

```bash
# Load and get top pro games
python3 -c "
import json
player_civ = 'english'  # from step 1

with open('reference_data/english_pro_games.json') as f:
    games = json.load(f)

# Filter: wins only, sort by rating (highest first)
wins = [g for g in games if g.get('result') == 'win']
wins.sort(key=lambda x: x.get('rating', 0), reverse=True)

# Get top 3-5 games for comparison
top_games = wins[:5]
for i, g in enumerate(top_games, 1):
    print(f'{i}. Rating: {g.get(\"rating\")}, Map: {g.get(\"map\")}, URL: {g.get(\"url\")}')
"
```

**Goal:** Compare player against **3-5 Pro games** and show:
- Average values (e.g., average feudal time)
- Best/Worst case ranges
- Consistent patterns across Pro games

### 3. Fetch Multiple Pro Games' Build Orders

```bash
# Player's game (already fetched in step 1)
python3 scripts/fetch_game_data.py --url "<player_url>" --compare --json > /tmp/player_game.json

# Pro's games (fetch 3-5 for statistical comparison)
for game_url in "<pro_game1_url>" "<pro_game2_url>" "<pro_game3_url>"; do
    python3 scripts/fetch_game_data.py --url "$game_url" --compare --json > /tmp/pro_game_$(date +%s).json
done
```

Each `--compare` output includes both players' build orders.

### 4. Compare & Analyze (Across Multiple Pro Games)

**Extract key metrics and calculate statistics:**

| Metric | You | Pro Avg | Pro Best | Pro Range | Delta | Status |
|--------|-----|---------|----------|-----------|-------|--------|
| Feudal Age | X:XX | Y:YY | Best:Y:YY | Y:YY-Y:YY | +Zs | 🔴/🟡/🟢 |
| Castle Age | X:XX | Y:YY | Best:Y:YY | Y:YY-Y:YY | +Zs | 🔴/🟡/🟢 |
| Villagers @10min | N | M | Best:M | M-M | -P | 🔴/🟡/🟢 |
| TC idle time | Xs | Ys | Best:Ys | Ys-Ys | +Zs | 🔴/🟡/🟢 |
| Total Villagers | N | M | Best:M | M-M | -P | 🔴/🟡/🟢 |

**Status indicators:**
- 🔴 Significant issue (delta > 60s or >20%)
- 🟡 Minor issue (delta 30-60s)
- 🟢 Good (delta < 30s)

**Deep Pattern Analysis:**

1. **TC Idle Time Distribution** — Most important for Gold/Plat
   - Extract villager `finished` timestamps from each game
   - Find gaps > 25s between consecutive villagers
   - **Analyze distribution:**
     - Total idle time (sum of all gaps)
     - Number of idle incidents (how many times TC stopped)
     - Longest single idle gap (worst moment)
     - When did idle occur? (early game vs late game)
   - **Calculate:** Average, Best, and Range across Pro games
   - **Visual:** Show timeline of villager production gaps

2. **Age-up Timing & Consistency**
   - Extract age upgrade times from build order (age icons)
   - Compare to benchmarks: Feudal 4:30-5:00, Castle 12:00-14:00
   - **Show:** How consistent are Pros across multiple games?
   - **Calculate:** Standard deviation - are Pros consistent or variable?

3. **Military Production Timeline**
   - When does military production start? (first military unit)
   - Production rate: units/minute in each age (Feudal, Castle, Imperial)
   - **Key milestones:**
     - First military unit time
     - 10 military units time
     - 50 military units time
   - **Compare:** Does player produce military too early (economy hurt) or too late (vulnerable)?

4. **Unit Composition Analysis**
   - Extract all military units from build order
   - **Calculate composition:**
     - % Archers vs % Cavalry vs % Infantry
     - Unique units (e.g., Longbowman for English)
     - Siege units count
   - **Compare:** Is player's army composition balanced or skewed?
   - **Pro patterns:** What unit mixes do Pros prefer?

5. **Building Priority Pattern**
   - Extract building construction times
   - **Analyze:**
     - First military building time (Barracks/Archery Range/Stable)
     - Farm expansion rate (how fast are farms added?)
     - Gold mining camps built
     - Defensive structures (Outposts, Towers)
   - **Pro patterns:** When do Pros build key buildings?

6. **Resource Imbalance Detection**
   - **Signs of resource imbalance:**
     - High food idle time → not enough farms
     - Late gold mining camp → gold starvation
     - Too many early military units → economy stunted
   - **Compare:** Does player float resources (could have aged up faster)?

**Example Deep Analysis Code:**

```python
import json
import glob
from collections import defaultdict

def analyze_villager_production(build_order):
    """Analyze TC idle time distribution"""
    for item in build_order:
        if 'villager' in item.get('icon', '').lower():
            times = sorted([t for t in item.get('finished', []) if t > 0])

            gaps = []
            for i in range(1, len(times)):
                gap = times[i] - times[i-1]
                if gap > 25:
                    gaps.append({
                        'start': times[i-1],
                        'end': times[i],
                        'duration': gap - 25,  # Excess idle time
                        'when': times[i-1]  # When it happened
                    })

            return {
                'total_villagers': len(times),
                'total_idle': sum(g['duration'] for g in gaps),
                'idle_incidents': len(gaps),
                'longest_gap': max([g['duration'] for g in gaps]) if gaps else 0,
                'idle_timeline': gaps  # For visualization
            }
    return None

def analyze_military_production(build_order):
    """Analyze military unit production timeline"""
    military_units = []
    for item in build_order:
        if item.get('type') == 'Unit':
            icon = item.get('icon', '')
            if 'villager' not in icon.lower() and 'scout' not in icon.lower():
                times = [t for t in item.get('finished', []) if t > 0]
                for t in times:
                    military_units.append({
                        'time': t,
                        'unit': icon.split('/')[-1],
                        'type': classify_unit(icon)  # archer/cavalry/infantry
                    })

    military_units.sort(key=lambda x: x['time'])

    # Find milestones
    milestones = {}
    if len(military_units) > 0:
        milestones['first'] = military_units[0]['time']
    if len(military_units) >= 10:
        milestones['10_units'] = military_units[9]['time']
    if len(military_units) >= 50:
        milestones['50_units'] = military_units[49]['time']

    # Calculate composition
    composition = defaultdict(int)
    for unit in military_units:
        composition[unit['type']] += 1

    total = sum(composition.values())
    composition_pct = {k: v/total*100 for k, v in composition.items()}

    return {
        'total_units': len(military_units),
        'milestones': milestones,
        'composition': composition_pct,
        'timeline': military_units
    }

def classify_unit(icon):
    """Classify unit type from icon"""
    icon_lower = icon.lower()
    if any(x in icon_lower for x in ['archer', 'longbow', 'crossbow']):
        return 'archer'
    elif any(x in icon_lower for x in ['knight', 'horse', 'cavalry']):
        return 'cavalry'
    elif any(x in icon_lower for x in ['manatarms', 'spear', 'sword']):
        return 'infantry'
    return 'other'

# Analyze all pro games
pro_games = []
for file in glob.glob('/tmp/pro_game_*.json'):
    with open(file) as f:
        data = json.load(f)
        game = data['player']

        villager_analysis = analyze_villager_production(game['build_order'])
        military_analysis = analyze_military_production(game['build_order'])

        pro_games.append({
            'villager': villager_analysis,
            'military': military_analysis
        })

# Calculate aggregates
avg_idle = sum(g['villager']['total_idle'] for g in pro_games) / len(pro_games)
avg_first_military = sum(g['military']['milestones'].get('first', 999) for g in pro_games) / len(pro_games)

print(f"Pro avg TC idle: {avg_idle:.1f}s")
print(f"Pro avg first military: {avg_first_military:.1f}s")
```

### 5. Generate Report

Write to `analysis/compare_vs_pros_{date}.md`:

```markdown
# 🏰 Pro 对比报告 (多局深度分析)

## 对局信息
| | 你 | Pro 平均 |
|---|---|---|
| 文明 | {civ} | {civ} |
| 地图 | {map} | {maps} |
| 分析局数 | 1 | {num_games} |

## ⏱️ 时间对比
| 节点 | 你 | Pro 平均 | Pro 最佳 | Pro 范围 | 差距 | 评价 |
|------|----|----|----|----|------|------|
| 封建时代 | 5:22 | 4:30 | 4:15 | 4:15-4:45 | +67s | 🔴 太慢 |
| 城堡时代 | 17:35 | 13:20 | 12:45 | 12:45-14:00 | +265s | 🔴 太慢 |
| 帝王时代 | - | 24:00 | 22:30 | 22:30-25:30 | - | - |

## 👷 经济对比
| 指标 | 你 | Pro 平均 | Pro 最佳 | Pro 范围 | 差距 |
|------|----|----|----|----|------|
| 村民总数 | 52 | 110 | 125 | 95-125 | -58 |
| TC 空闲时间 | 381s | 75s | 40s | 40-120s | +306s |
| 10分钟时村民 | 28 | 40 | 45 | 35-45 | -12 |

## 🏹 军事生产对比
| 指标 | 你 | Pro 平均 | Pro 最佳 | Pro 范围 | 差距 |
|------|----|----|----|----|------|
| 首兵时间 | 5:45 | 5:00 | 4:30 | 4:30-5:30 | +45s |
| 10兵时间 | 12:00 | 8:30 | 7:45 | 7:45-9:30 | +225s |
| 总单位数 | 120 | 180 | 220 | 150-220 | -60 |
| 弓兵占比 | 65% | 55% | 70% | 40-70% | +10% |

## 📊 TC 空闲时间详细分析

### 你
- 总空闲时间: 381秒
- 空闲次数: 15次
- 最长单次: 120秒
- 空闲时间线:
  - 2:15 - 3:45 (90秒) → 早期能致命
  - 8:30 - 10:00 (90秒) → 封建经济停滞
  - 15:00 - 16:30 (90秒) → 城堡经济雪球断档

### Pro 平均
- 总空闲时间: 75秒
- 空闲次数: 3次
- 最长单次: 35秒
- 空闲时间线:
  - 大多Pro只有2-3次短暂空闲
  - 空闲发生在换基地/转攻防时，可控

### 结论
你的TC空闲时间是Pro的 **5倍**，且最长单次空闲是Pro的 **3.4倍**。这是经济落后的根本原因。

## ⚔️ 军事构成分析

### 你的军队构成
```
长弓手 (Longbowman): 78 (65%)
骑士 (Knight): 24 (20%)
剑士 (Man-at-arms): 18 (15%)
```

### Pro 平均构成
```
长弓手: 99 (55%)
骑士: 54 (30%)
剑士: 27 (15%)
```

### 分析
- 你的兵种组合思路正确（Longbow为主力+骑士配合）
- 但总单位数少30%，正面战斗力不足
- Pro在保持相同构成的同时，经济支撑更多单位

### 军事生产时间线对比
| 时间点 | 你的累计单位 | Pro 平均累计 |
|--------|------------|-------------|
| 5分钟 | 2 | 5 |
| 10分钟 | 15 | 35 |
| 15分钟 | 45 | 90 |
| 20分钟 | 80 | 140 |

你的军事生产速度是Pro的 **50-60%**，直接导致战场劣势。

## 📊 Pro 数据来源

分析的Pro游戏:
1. **燕子宇** (2192 rating) - Dry Arabia, Win
   - 封建: 4:46, 城堡: 15:09, 村民: 135, TC空闲: 64s
   - 首兵: 4:50, 10兵: 8:20, 总单位: 195
2. **loueMT** (2366 rating) - Dry Arabia, Win
   - 封建: 4:15, 城堡: 13:10, 村民: 116, TC空闲: 90s
   - 首兵: 4:30, 10兵: 7:45, 总单位: 180
3. **燕子宇** (2205 rating) - Dry Arabia, Loss
   - 封建: 4:52, 城堡: 16:30, 村民: 98, TC空闲: 120s
   - 首兵: 5:10, 10兵: 9:00, 总单位: 150

## 🔍 核心差距

### 1. TC 空闲时间过长 (381秒 vs Pro 平均 75秒) ⚠️ 最严重
**你:** TC 在多个时间段有空闲，总空闲时间381秒
**Pro 平均:** 平均空闲75秒，最佳仅40秒
**Pro 范围:** 40-120秒 (即使最差的Pro也比你好)

**为什么重要:**
- 每秒TC闲置 = 损失0.5资源/秒 + 少产村民
- 381秒空闲 ≈ 少产15个村民 = 750资源采集能力损失
- 经济雪球效应：少村民→少资源→少兵→更难抢资源→恶性循环

**如何改进:**
- 养成每 25 秒看一眼 TC 的习惯
- 设置心理闹钟：上一农民出生后 25 秒必须按下一个
- 练习时只专注这一件事

### 2. 军事生产速度慢 (累计单位只有Pro的50-60%)
**你:** 10分钟时只有15个军事单位
**Pro 平均:** 10分钟时有35个军事单位

**为什么重要:**
- 10分钟是封建交战高峰期
- 15 vs 35 = 正面必输，哪怕操作更好
- Pro能抢资源、杀村民、拆建筑，你只能防守

**如何改进:**
- TC不停产 = 有钱造更多兵
- 封建后立即造兵营/弓箭场
- 不要卡人口：提前造房子

### 3. 封建升级晚了 67 秒 (vs Pro 平均)
**你:** 5:22 升封建
**Pro 平均:** 4:30 升封建
**Pro 最佳:** 4:15

**为什么重要:**
- 晚67秒 = 对手比你早67秒进入封建 = 可以早造兵营/弓箭场
- Pro 范围显示: 即使是较慢的Pro也能在4:45前升封建

**如何改进:**
- 检查 4:00 时是否有 500 食物
- 如果资源够但没升，是操作问题
- 如果资源不够，是采集分配问题

## 💡 今日练习建议

### 优先级1: TC不停产 (最重要!)
- 开AI局，**只关注TC**
- 目标: 15分钟内100+村民
- 练习时可以在心里数 "25秒到了没"
- 记录每局TC空闲时间，目标降到60秒以下

### 优先级2: 早期军事生产
- 封建后立即造兵营
- 保持持续造兵，不要停
- 目标: 10分钟时30+军事单位

### 优先级3: 时间点检查
记住这三个关键检查点:
- **4:00** - 应该有500食物，准备升封建
- **10:00** - 应该有30+村民、30+军事单位
- **15:00** - 应该接近或进入城堡时代

### VOD 参考
- [燕子宇 最佳局]({url1}) - 4:46 封建, 64s TC空闲
- [loueMT 最佳局]({url2}) - 4:15 封建, 90s TC空闲

## ✅ 你做得好的地方
- 封建升级时间在Pro范围内 (虽然偏慢)
- 兵种组合思路正确 (Longbow + 骑士)
- 科技升级全部完成
```

### 6. Output Summary

Print to console:

```
📊 对比总结 (基于 {N} 局 Pro 游戏)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
你 vs Pro 平均 (2192-2366 rating)

🔴 3 个核心问题:
1. TC 空闲 381秒 vs Pro 平均 75秒 (最佳40秒) → 少产 15 村民
2. 封建晚 67秒 (5:22 vs Pro 平均 4:30) → 军事起步慢
3. 村民 52 vs Pro 平均 110 → 经济只有 Pro 的 47%

🟡 Pro 范围参考:
- 封建时间: 4:15 - 4:52 (你 5:22, 慢了30-67秒)
- TC空闲: 40s - 120s (你 381s, 是Pro的3-9倍)
- 村民总数: 95 - 125 (你 52, 少了43-73个)

✅ 下一步: 专项练习 TC 不停产
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Notes

- Use Chinese for the coaching report
- Be specific with numbers: "Pro 升封建 4:15，你 5:22，慢了 67 秒"
- Focus on **learnable patterns**, not mechanical speed
- If rating gap is large (>400), note that some differences are APM-related
- Always include actionable practice suggestions
- Reference game URLs for user to review themselves
