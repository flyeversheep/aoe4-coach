import asyncio
import json
from aoe4world_client import AoE4WorldClient

async def analyze_military():
    async with AoE4WorldClient() as client:
        summary = await client.get_game_summary(profile_id='17689761', game_id='220682882', sig='8ba87c0c5eee75b8a28fa79e643f54e40eaea577')
        game = client.parse_game_summary(summary, profile_id='17689761')

        # 解析双方的军事单位
        player_units = {}
        opponent_units = {}

        for bo in game.build_order:
            icon = bo.get('icon', '')
            unit_type = bo.get('type', '')
            finished = bo.get('finished', [])

            if unit_type == 'Unit' and 'villager' not in icon.lower() and 'scout' not in icon.lower():
                unit_name = icon.split('/')[-1]
                player_units[unit_name] = len(finished)

        for bo in game.opponent_build_order:
            icon = bo.get('icon', '')
            unit_type = bo.get('type', '')
            finished = bo.get('finished', [])

            if unit_type == 'Unit' and 'villager' not in icon.lower() and 'scout' not in icon.lower():
                unit_name = icon.split('/')[-1]
                opponent_units[unit_name] = len(finished)

        print('=== 你的军事单位 ===')
        for unit, count in sorted(player_units.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f'  {unit}: {count}')
        print(f'  总计: {sum(player_units.values())}')

        print('')
        print('=== 对手的军事单位 ===')
        for unit, count in sorted(opponent_units.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f'  {unit}: {count}')
        print(f'  总计: {sum(opponent_units.values())}')

        print('')
        print('=== 单位类型对比 ===')
        all_types = set(player_units.keys()) | set(opponent_units.keys())
        for unit_type in all_types:
            player_count = player_units.get(unit_type, 0)
            opponent_count = opponent_units.get(unit_type, 0)
            diff = player_count - opponent_count
            if diff != 0:
                if diff > 0:
                    print(f'  {unit_type}: 你{player_count} vs 对手{opponent_count} (你多{diff})')
                else:
                    print(f'  {unit_type}: 你{player_count} vs 对手{opponent_count} (你少{-diff})')

        # 分析关键单位类型
        print('')
        print('=== 兵种分类对比 ===')
        player_longbow = sum([v for k, v in player_units.items() if 'archer' in k])
        opp_longbow = sum([v for k, v in opponent_units.items() if 'archer' in k])
        player_knight = sum([v for k, v in player_units.items() if 'knight' in k or 'horseman' in k])
        opp_knight = sum([v for k, v in opponent_units.items() if 'knight' in k or 'horseman' in k])
        player_infantry = sum([v for k, v in player_units.items() if 'manatarms' in k or 'spearman' in k])
        opp_infantry = sum([v for k, v in opponent_units.items() if 'manatarms' in k or 'spearman' in k])
        player_siege = sum([v for k, v in player_units.items() if 'trebuchet' in k or 'ram' in k or 'ribauldequin' in k])
        opp_siege = sum([v for k, v in opponent_units.items() if 'trebuchet' in k or 'ram' in k or 'ribauldequin' in k])

        print(f'  远程(长弓): 你{player_longbow} vs 对手{opp_longbow}')
        print(f'  骑士: 你{player_knight} vs 对手{opp_knight}')
        print(f'  步兵: 你{player_infantry} vs 对手{opp_infantry}')
        print(f'  攻城: 你{player_siege} vs 对手{opp_siege}')

        # 分析生产建筑数量（通过单位生产节奏推测）
        print('')
        print('=== 军事分数对比 ===')
        print(f'  你的军事分: {game.final_score.get("military", 0)}')
        # 从summary获取对手分数
        for player in summary.get('players', []):
            if str(player.get('profileId')) != '17689761':
                opp_scores = player.get('scores', {})
                print(f'  对手军事分: {opp_scores.get("military", 0)}')

asyncio.run(analyze_military())
