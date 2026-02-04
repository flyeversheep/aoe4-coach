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

@dataclass
class BuildOrderItem:
    id: str
    icon: str
    pbgid: int
    type: str  # Unit, Building, Age, Upgrade, Animal
    finished: List[int]  # timestamps in seconds
    constructed: List[int]
    destroyed: List[int]

@dataclass
class GameSummary:
    game_id: int
    duration: int
    map_name: str
    win_reason: str

    # Player data
    player_name: str
    player_civ: str
    player_result: str
    player_apm: int

    # Build order
    build_order: List[Dict[str, Any]]

    # Age up timings
    feudal_age_time: Optional[int]
    castle_age_time: Optional[int]
    imperial_age_time: Optional[int]

    # Resources
    total_resources_gathered: Dict[str, int]
    total_resources_spent: Dict[str, int]

    # Scores
    final_score: Dict[str, int]

    # Opponent
    opponent_name: str
    opponent_civ: str

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
        # Note: connector is closed by the session
    
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
                print(f"DEBUG get_player_games: Response type={type(data)}, keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                # Handle both formats: list directly or dict with "games" key
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("games", [])
                return []
            return []

    async def get_game_summary(
        self,
        profile_id: str,
        game_id: str,
        sig: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed game summary including build order

        Args:
            profile_id: Player profile ID
            game_id: Game ID to fetch
            sig: Optional signature for authentication (required for private games)

        Returns:
            Dictionary with game summary data including build order, or None if not found
        """
        # Build URL - summary endpoint uses the web URL format
        url = f"https://aoe4world.com/players/{profile_id}/games/{game_id}/summary"
        params = {"camelize": "true"}
        if sig:
            params["sig"] = sig

        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                try:
                    data = await response.json()
                    print(f"DEBUG get_game_summary: Successfully fetched summary for game {game_id}")
                    return data
                except Exception as e:
                    print(f"DEBUG get_game_summary: Error parsing JSON: {e}")
                    return None
            else:
                print(f"DEBUG get_game_summary: HTTP {response.status} for game {game_id}")
                return None

    def parse_game_summary(self, summary_data: Dict[str, Any], profile_id: str) -> Optional[GameSummary]:
        """Parse game summary data into GameSummary object"""
        try:
            if not summary_data or "players" not in summary_data:
                return None

            # Find the player's data
            player_data = None
            opponent_data = None

            for player in summary_data["players"]:
                if str(player.get("profileId")) == str(profile_id):
                    player_data = player
                else:
                    opponent_data = player

            if not player_data:
                print(f"DEBUG parse_game_summary: Player {profile_id} not found in game data")
                return None

            # Extract age up timings from actions
            actions = player_data.get("actions", {})
            feudal_age_time = actions.get("feudalAge", [None])[0]
            castle_age_time = actions.get("castleAge", [None])[0]
            imperial_age_time = actions.get("imperialAge", [None])[0]

            return GameSummary(
                game_id=summary_data.get("gameId"),
                duration=summary_data.get("duration", 0),
                map_name=summary_data.get("mapName", "Unknown"),
                win_reason=summary_data.get("winReason", "Unknown"),
                player_name=player_data.get("name", "Unknown"),
                player_civ=player_data.get("civilization", "Unknown"),
                player_result=player_data.get("result", "unknown"),
                player_apm=player_data.get("apm", 0),
                build_order=player_data.get("buildOrder", []),
                feudal_age_time=feudal_age_time,
                castle_age_time=castle_age_time,
                imperial_age_time=imperial_age_time,
                total_resources_gathered=player_data.get("totalResourcesGathered", {}),
                total_resources_spent=player_data.get("totalResourcesSpent", {}),
                final_score=player_data.get("scores", {}),
                opponent_name=opponent_data.get("name", "Unknown") if opponent_data else "Unknown",
                opponent_civ=opponent_data.get("civilization", "Unknown") if opponent_data else "Unknown"
            )
        except Exception as e:
            print(f"Error parsing game summary: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_game(self, game_data: Dict, profile_id: str) -> Optional[Game]:
        """Parse game data and extract player-specific info"""
        try:
            # Ensure game_data is a dict
            if not isinstance(game_data, dict):
                print(f"DEBUG parse_game: game_data is not dict, type={type(game_data)}")
                return None
                
            teams = game_data.get("teams", [])
            if not teams:
                print(f"DEBUG parse_game: No teams found in game_data")
                return None
                
            print(f"DEBUG parse_game: Found {len(teams)} teams")
            
            # Find the player in teams
            player_info = None
            opponent_info = None
            
            for team in teams:
                # Handle both dict format {"players": [...]} and list format [...]
                if isinstance(team, dict):
                    players = team.get("players", [])
                elif isinstance(team, list):
                    players = team
                else:
                    print(f"DEBUG parse_game: Unexpected team type: {type(team)}")
                    continue

                print(f"DEBUG parse_game: Team has {len(players)} players")
                for player_wrapper in players:
                    if not isinstance(player_wrapper, dict):
                        print(f"DEBUG parse_game: Player wrapper is not dict, type={type(player_wrapper)}")
                        continue

                    # Extract actual player data from wrapper
                    player = player_wrapper.get('player', player_wrapper)
                    if not isinstance(player, dict):
                        print(f"DEBUG parse_game: Player data is not dict, type={type(player)}")
                        continue

                    print(f"DEBUG parse_game: Player keys: {list(player.keys())}")
                    print(f"DEBUG parse_game: Checking player {player.get('profile_id')} vs {profile_id}")
                    if str(player.get("profile_id")) == str(profile_id):
                        player_info = player
                        print(f"DEBUG parse_game: Found target player")
                    else:
                        # Take first opponent found
                        if not opponent_info:
                            opponent_info = player
            
            if not player_info:
                print(f"DEBUG parse_game: Player not found in game")
                return None
            
            # Parse date safely
            started_at_str = game_data.get("started_at", "")
            try:
                started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            except Exception as date_err:
                print(f"DEBUG parse_game: Date parse error: {date_err}, using now")
                started_at = datetime.now()
            
            return Game(
                game_id=game_data.get("game_id", ""),
                started_at=started_at,
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
            import traceback
            traceback.print_exc()
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
