"""
AoE4 World API Client
Fetches player data and match history from AoE4 World
"""
import aiohttp
import ssl
import certifi
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

AOE4WORLD_API_BASE = "https://aoe4world.com/api/v0"

# Create SSL context with proper certificate verification
ssl_context = ssl.create_default_context(cafile=certifi.where())

@dataclass
class Player:
    profile_id: int
    name: str
    steam_id: Optional[str]
    country: Optional[str]
    avatar_url: Optional[str]
    
@dataclass
class Game:
    game_id: str
    started_at: datetime
    duration: int  # seconds
    map: str
    kind: str  # rm_solo, rm_team, etc
    
    # Player-specific data
    player_civ: str
    player_result: str  # win, loss
    player_rating: int
    player_rating_diff: int
    
    # Opponent data
    opponent_name: str
    opponent_civ: str
    opponent_rating: int

class AoE4WorldClient:
    """Client for AoE4 World API"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        # Create connector with proper SSL context
        self.connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(connector=self.connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.connector:
            self.connector.close()
    
    async def get_player(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get player profile by profile_id or steam_id"""
        url = f"{AOE4WORLD_API_BASE}/players/{profile_id}"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None
    
    async def get_player_games(
        self, 
        profile_id: str, 
        limit: int = 10,
        leaderboard: str = "rm_solo"
    ) -> List[Dict[str, Any]]:
        """Get player's recent games"""
        url = f"{AOE4WORLD_API_BASE}/players/{profile_id}/games"
        params = {
            "limit": limit,
            "leaderboard": leaderboard
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("games", [])
            return []
    
    def parse_game(self, game_data: Dict, profile_id: str) -> Optional[Game]:
        """Parse game data and extract player-specific info"""
        try:
            teams = game_data.get("teams", [])
            
            # Find the player in teams
            player_info = None
            opponent_info = None
            
            for team in teams:
                for player in team.get("players", []):
                    if str(player.get("profile_id")) == str(profile_id):
                        player_info = player
                    else:
                        # Take first opponent found
                        if not opponent_info:
                            opponent_info = player
            
            if not player_info:
                return None
            
            return Game(
                game_id=game_data.get("game_id", ""),
                started_at=datetime.fromisoformat(
                    game_data.get("started_at", "").replace("Z", "+00:00")
                ),
                duration=game_data.get("duration", 0),
                map=game_data.get("map", "Unknown"),
                kind=game_data.get("kind", "unknown"),
                player_civ=player_info.get("civilization", "Unknown"),
                player_result=player_info.get("result", "unknown"),
                player_rating=player_info.get("rating", 0),
                player_rating_diff=player_info.get("rating_diff", 0),
                opponent_name=opponent_info.get("name", "Unknown") if opponent_info else "Unknown",
                opponent_civ=opponent_info.get("civilization", "Unknown") if opponent_info else "Unknown",
                opponent_rating=opponent_info.get("rating", 0) if opponent_info else 0
            )
        except Exception as e:
            print(f"Error parsing game: {e}")
            return None
    
    def analyze_performance(self, games: List[Game]) -> Dict[str, Any]:
        """Analyze player performance from games"""
        if not games:
            return {}
        
        total_games = len(games)
        wins = sum(1 for g in games if g.player_result == "win")
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        # Civilization stats
        civ_stats = {}
        for game in games:
            civ = game.player_civ
            if civ not in civ_stats:
                civ_stats[civ] = {"games": 0, "wins": 0}
            civ_stats[civ]["games"] += 1
            if game.player_result == "win":
                civ_stats[civ]["wins"] += 1
        
        # Map stats
        map_stats = {}
        for game in games:
            map_name = game.map
            if map_name not in map_stats:
                map_stats[map_name] = {"games": 0, "wins": 0}
            map_stats[map_name]["games"] += 1
            if game.player_result == "win":
                map_stats[map_name]["wins"] += 1
        
        # Calculate win rates
        for civ in civ_stats:
            civ_stats[civ]["win_rate"] = (
                civ_stats[civ]["wins"] / civ_stats[civ]["games"] * 100
            )
        
        for map_name in map_stats:
            map_stats[map_name]["win_rate"] = (
                map_stats[map_name]["wins"] / map_stats[map_name]["games"] * 100
            )
        
        # Rating trend
        rating_changes = [g.player_rating_diff for g in games]
        avg_rating_change = sum(rating_changes) / len(rating_changes) if rating_changes else 0
        
        return {
            "total_games": total_games,
            "wins": wins,
            "losses": total_games - wins,
            "win_rate": round(win_rate, 1),
            "civilization_stats": civ_stats,
            "map_stats": map_stats,
            "avg_rating_change": round(avg_rating_change, 1),
            "current_rating": games[0].player_rating if games else 0
        }
