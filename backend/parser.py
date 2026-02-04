# AoE IV Replay Parser MVP

import struct
import json
import zipfile
from io import BytesIO
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class GameEvent:
    timestamp: int  # milliseconds
    event_type: str
    player_id: int
    data: Dict[str, Any]

@dataclass
class PlayerStats:
    player_id: int
    civ: str
    name: str
    team: int
    
    # Economy
    villager_count: List[tuple]  # (timestamp, count)
    resources_gathered: Dict[str, int]  # food, wood, gold, stone
    
    # Military
    military_count: List[tuple]
    units_created: Dict[str, int]
    
    # Tech
    age_up_times: List[int]  # timestamps for each age up
    technologies_researched: List[tuple]  # (timestamp, tech_name)
    
    # Buildings
    tc_count: List[tuple]
    military_buildings: int

class AoE4ReplayParser:
    """Parse AoE IV replay files (.aoe2record)"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.raw_data = None
        self.game_info = {}
        self.players: List[PlayerStats] = []
        self.events: List[GameEvent] = []
    
    def parse(self) -> Dict[str, Any]:
        """Main parse function"""
        with open(self.file_path, 'rb') as f:
            raw = f.read()
        
        # Try to parse as zip (newer format)
        try:
            with zipfile.ZipFile(BytesIO(raw), 'r') as z:
                # Find the main replay data
                for name in z.namelist():
                    if 'replay' in name.lower() or name.endswith('.json'):
                        self.raw_data = json.loads(z.read(name))
                        break
        except zipfile.BadZipFile:
            # Old format - binary parsing needed
            self.raw_data = self._parse_binary(raw)
        
        if not self.raw_data:
            raise ValueError("Could not parse replay file")
        
        self._extract_game_info()
        self._extract_players()
        self._extract_events()
        
        return {
            'game_info': self.game_info,
            'players': self.players,
            'events': self.events,
            'summary': self._generate_summary()
        }
    
    def _parse_binary(self, data: bytes) -> Dict:
        """Parse binary replay format (simplified MVP version)"""
        # MVP: Return placeholder - full binary parsing is complex
        return {
            'version': 'unknown',
            'duration': 0,
            'players': []
        }
    
    def _extract_game_info(self):
        """Extract basic game information"""
        info = self.raw_data.get('game_info', {})
        self.game_info = {
            'map_name': info.get('map_name', 'Unknown'),
            'game_duration': info.get('duration', 0),
            'game_version': info.get('version', 'Unknown'),
            'game_date': info.get('date', datetime.now().isoformat()),
            'game_mode': info.get('game_mode', '1v1'),
        }
    
    def _extract_players(self):
        """Extract player statistics"""
        players_data = self.raw_data.get('players', [])
        
        for i, pdata in enumerate(players_data):
            stats = PlayerStats(
                player_id=i,
                civ=pdata.get('civilization', 'Unknown'),
                name=pdata.get('name', f'Player {i+1}'),
                team=pdata.get('team', 0),
                villager_count=[],
                resources_gathered={'food': 0, 'wood': 0, 'gold': 0, 'stone': 0},
                military_count=[],
                units_created={},
                age_up_times=[],
                technologies_researched=[],
                tc_count=[],
                military_buildings=0
            )
            self.players.append(stats)
    
    def _extract_events(self):
        """Extract game events"""
        events_data = self.raw_data.get('events', [])
        
        for edata in events_data:
            event = GameEvent(
                timestamp=edata.get('timestamp', 0),
                event_type=edata.get('type', 'unknown'),
                player_id=edata.get('player_id', -1),
                data=edata.get('data', {})
            )
            self.events.append(event)
            
            # Update player stats based on events
            self._process_event(event)
    
    def _process_event(self, event: GameEvent):
        """Process individual game events to update stats"""
        if event.player_id < 0 or event.player_id >= len(self.players):
            return
        
        player = self.players[event.player_id]
        
        if event.event_type == 'unit_created':
            unit_type = event.data.get('unit_type', '')
            if 'villager' in unit_type.lower():
                # Update villager count
                pass
            player.units_created[unit_type] = player.units_created.get(unit_type, 0) + 1
            
        elif event.event_type == 'age_up':
            player.age_up_times.append(event.timestamp)
            
        elif event.event_type == 'research_complete':
            tech = event.data.get('technology', '')
            player.technologies_researched.append((event.timestamp, tech))
            
        elif event.event_type == 'building_complete':
            building = event.data.get('building', '')
            if 'town_center' in building.lower():
                # Update TC count
                pass
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate game summary statistics"""
        return {
            'total_events': len(self.events),
            'player_count': len(self.players),
            'civilizations': [p.civ for p in self.players],
            'game_duration_formatted': self._format_duration(
                self.game_info.get('game_duration', 0)
            )
        }
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format seconds to MM:SS"""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"

# Simple test
if __name__ == '__main__':
    # Create sample data for testing
    sample_data = {
        'game_info': {
            'map_name': 'Arabia',
            'duration': 1800,  # 30 minutes
            'version': '11.0.782',
            'date': '2024-02-03T12:00:00Z',
            'game_mode': '1v1'
        },
        'players': [
            {'name': 'Player1', 'civilization': 'English', 'team': 1},
            {'name': 'Player2', 'civilization': 'French', 'team': 2}
        ],
        'events': [
            {'timestamp': 0, 'type': 'game_start', 'player_id': -1, 'data': {}},
            {'timestamp': 60000, 'type': 'age_up', 'player_id': 0, 'data': {'age': 2}},
            {'timestamp': 90000, 'type': 'age_up', 'player_id': 1, 'data': {'age': 2}},
        ]
    }
    
    print("AoE IV Replay Parser MVP loaded successfully!")
    print(f"Sample data: {len(sample_data['players'])} players")
