"""
AoE4 Data Lookup
Fetches unit, building, and technology data from data.aoe4world.com
and provides pbgid → name mapping for build order display.
"""
import aiohttp
import ssl
import certifi
from typing import Dict, Optional
from dataclasses import dataclass

DATA_API_BASE = "https://data.aoe4world.com"

# Create SSL context with proper certificate verification
ssl_context = ssl.create_default_context(cafile=certifi.where())


@dataclass
class EntityData:
    """Data for a game entity (unit, building, technology)"""
    pbgid: int
    name: str
    base_id: str
    entity_type: str  # "unit", "building", "technology"
    civs: list
    age: int


class AoE4DataLookup:
    """
    Lookup service for AoE4 game data.
    Fetches data on startup and provides fast pbgid → name lookups.
    """

    def __init__(self):
        self._pbgid_to_entity: Dict[int, EntityData] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def entity_count(self) -> int:
        return len(self._pbgid_to_entity)

    async def load(self) -> bool:
        """
        Load all entity data from the AoE4 World data API.
        Returns True if successful, False otherwise.
        """
        print("INFO: Loading AoE4 data from data.aoe4world.com...")

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Fetch all data types in parallel
            endpoints = [
                ("units", f"{DATA_API_BASE}/units/all.json"),
                ("buildings", f"{DATA_API_BASE}/buildings/all.json"),
                ("technologies", f"{DATA_API_BASE}/technologies/all.json"),
            ]

            total_loaded = 0

            for entity_type, url in endpoints:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            # Data is wrapped in a 'data' key
                            entities = response_data.get("data", []) if isinstance(response_data, dict) else response_data
                            count = self._process_entities(entities, entity_type)
                            total_loaded += count
                            print(f"INFO: Loaded {count} {entity_type}")
                        else:
                            print(f"WARN: Failed to fetch {entity_type}: HTTP {response.status}")
                except Exception as e:
                    print(f"ERROR: Failed to fetch {entity_type}: {e}")

            self._loaded = total_loaded > 0
            print(f"INFO: AoE4 data loaded: {total_loaded} entities total")
            return self._loaded

    def _process_entities(self, data: list, entity_type: str) -> int:
        """Process a list of entities and add to lookup table"""
        count = 0
        for item in data:
            pbgid = item.get("pbgid")
            if pbgid is None:
                continue

            entity = EntityData(
                pbgid=pbgid,
                name=item.get("name", "Unknown"),
                base_id=item.get("baseId", item.get("id", "")),
                entity_type=entity_type,
                civs=item.get("civs", []),
                age=item.get("age", 0)
            )

            self._pbgid_to_entity[pbgid] = entity
            count += 1

        return count

    def get_name(self, pbgid: int, fallback: Optional[str] = None) -> str:
        """
        Get the display name for a pbgid.

        Args:
            pbgid: The property bag group ID
            fallback: Fallback name if pbgid not found (e.g., extracted from icon path)

        Returns:
            The display name, or fallback if not found
        """
        entity = self._pbgid_to_entity.get(pbgid)
        if entity:
            return entity.name
        return fallback or f"Unknown ({pbgid})"

    def get_entity(self, pbgid: int) -> Optional[EntityData]:
        """Get full entity data for a pbgid"""
        return self._pbgid_to_entity.get(pbgid)

    def enrich_build_order(self, build_order: list) -> list:
        """
        Enrich build order items with proper names from the lookup.

        Args:
            build_order: List of build order items from API

        Returns:
            Enriched build order with 'name' field added to each item
        """
        enriched = []
        for item in build_order:
            # Create a copy to avoid modifying original
            enriched_item = dict(item)

            # Get pbgid and try to look up name
            pbgid = item.get("pbgid")
            if pbgid:
                # Get name from lookup, falling back to icon extraction
                icon = item.get("icon", "")
                icon_name = icon.split("/")[-1].replace("_", " ") if icon else None
                enriched_item["name"] = self.get_name(pbgid, icon_name)
            else:
                # No pbgid, fall back to icon extraction
                icon = item.get("icon", "")
                enriched_item["name"] = icon.split("/")[-1].replace("_", " ") if icon else "Unknown"

            enriched.append(enriched_item)

        return enriched


# Global instance for use across the application
aoe4_data = AoE4DataLookup()
