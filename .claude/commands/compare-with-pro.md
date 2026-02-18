# Compare With Pro

Compare a player's game against a professional/high-rated player's game with the same civilization and strategy, identifying pattern differences and generating improvement suggestions.

## Inputs

- **Game URL**: $ARGUMENTS
  - AoE4 World game URL for the player's game (required)
  - Optional flag `--pro <name>`: specific pro to compare against (e.g., `--pro 燕子宇`, `--pro loueMT`)

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

### 2. Find Reference Game

**If `--pro` specified:**
Use that player's games from `reference_data/english_pro_games.json`.

**If no pro specified (auto-select):**
1. Load `reference_data/english_pro_games.json`
2. Filter by:
   - Same civilization
   - Similar rating tier (±200 rating is ideal for learnable patterns)
   - Preferably a **win** (shows good execution)
3. If multiple matches, pick the highest-rated one

```bash
# Load and filter pro games
python3 -c "
import json
player_civ = 'english'  # from step 1
player_rating = 821  # from step 1

with open('reference_data/english_pro_games.json') as f:
    games = json.load(f)

# Filter: same civ, rating within 200-500 above player
filtered = [g for g in games 
            if g.get('rating', 0) > player_rating 
            and g.get('rating', 0) < player_rating + 500]

# Sort by rating closest to player + 300
filtered.sort(key=lambda x: abs(x.get('rating', 0) - (player_rating + 300)))
print(json.dumps(filtered[:3], indent=2))
"
```

### 3. Fetch Both Games' Build Orders

```bash
# Player's game (already fetched in step 1)
python3 scripts/fetch_game_data.py --url "<player_url>" --compare --json

# Pro's game
python3 scripts/fetch_game_data.py --url "<pro_game_url>" --compare --json
```

Each `--compare` output includes both players' build orders.

### 4. Compare & Analyze

**Extract key metrics:**

| Metric | You | Pro | Delta | Status |
|--------|-----|-----|-------|--------|
| Feudal Age | X:XX | Y:YY | +Zs | 🔴/🟡/🟢 |
| Castle Age | X:XX | Y:YY | +Zs | 🔴/🟡/🟢 |
| Villagers @10min | N | M | -P | 🔴/🟡/🟢 |
| TC idle time | Xs | Ys | +Zs | 🔴/🟡/🟢 |
| APM | X | Y | -Z | - |

**Status indicators:**
- 🔴 Significant issue (delta > 60s or >20%)
- 🟡 Minor issue (delta 30-60s)
- 🟢 Good (delta < 30s)

**Deep analysis:**

1. **TC Idle Time** — Most important for Gold/Plat
   - Extract villager `finished` timestamps
   - Find gaps > 25s between consecutive villagers
   - Sum total idle time

2. **Age-up Timing**
   - Extract `feudalAge`, `castleAge` from `actions`
   - Compare to benchmarks: Feudal 4:30-5:00, Castle 12:00-14:00

3. **Resource Allocation**
   - Compare `resources_gathered` ratios
   - Food/Wood/Gold balance

4. **Build Order Pattern**
   - What buildings/units does Pro prioritize?
   - When does Pro start military production?

### 5. Generate Report

Write to `analysis/compare_vs_{pro_name}_{date}.md`:

```markdown
# 🏰 Pro 对比报告

## 对局信息
| | 你 | {Pro Name} |
|---|---|---|
| 文明 | {civ} | {civ} |
| 分数 | {rating} | {pro_rating} (+{diff}) |
| 地图 | {map} | {map} |
| 时长 | {mins}min | {mins}min |
| 结果 | {result} | {result} |

## ⏱️ 时间对比
| 节点 | 你 | Pro | 差距 | 评价 |
|------|----|----|------|------|
| 封建 | 5:22 | 4:15 | +67s | 🔴 太慢 |
| 城堡 | 17:35 | 13:10 | +265s | 🔴 太慢 |
| 帝王 | - | - | - | - |

## 👷 经济对比
| 指标 | 你 | Pro | 差距 |
|------|----|----|------|
| 村民总数 | 52 | 116 | -64 |
| TC 空闲时间 | 381s | 40s | +341s |
| 10分钟时村民 | 28 | 45 | -17 |

## 🔍 核心差距

### 1. TC 空闲时间过长 (381秒)
**你:** TC 在 709s-1090s 期间完全没有产村民，这段时间只有 0 个新村民。
**Pro:** 最大空闲间隔只有 40 秒，持续产出。
**为什么重要:** 每秒少 1 个农民 = 少 0.5 资源/秒 = 经济雪球越滚越大。
**如何改进:** 
- 养成每 25 秒看一眼 TC 的习惯
- 设置心理闹钟：上一农民出生后 25 秒必须按下一个
- 练习时只专注这一件事

### 2. 封建升级晚了 67 秒
**你:** 5:22 升封建
**Pro:** 4:15 升封建
**为什么重要:** 晚 67 秒 = 对手比你早 67 秒进入封建 = 可以早造兵营/弓箭场
**如何改进:** 
- 检查 4:00 时是否有 200 食物
- 如果资源够但没升，是操作问题
- 如果资源不够，是采集分配问题

### 3. 村民总数差距 (52 vs 116)
**你:** 只产了 52 个村民
**Pro:** 产了 116 个村民
**为什么重要:** 村民数量直接决定经济上限。52 个 vs 116 个 = 2 倍经济差距。
**如何改进:** 
- 这是 TC 空闲时间问题的直接结果
- 解决 TC 空闲 = 自然增加村民数量

## 💡 今日练习建议
1. **专项训练:** 开一局 AI，只专注 TC 不停产，目标是 15 分钟 100+ 村民
2. **看 Rep 时间点:** 记住 4:00、10:00、15:00 三个检查点
3. **VOD 参考:** [Pro 的对局 VOD]({vod_url})

## ✅ 你做得好的地方
- 科技升级全部完成（虽然晚了）
- 军事单位种类选择合理
```

### 6. Output Summary

Print to console:

```
📊 对比总结
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
你 vs 燕子宇 (2205 vs 821, +1384 rating差距)

🔴 3 个核心问题:
1. TC 空闲 381 秒 vs Pro 40 秒 → 少产 64 村民
2. 封建晚 67 秒 → 军事起步慢
3. 村民 52 vs 116 → 经济雪球差距

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
