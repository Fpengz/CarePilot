from pydantic import BaseModel
from typing import List, Dict


class BlockScore(BaseModel):
    block_id: str
    postal_code_prefix: str
    sugar_reduction_points: int = 0
    sodium_reduction_points: int = 0
    active_residents: int = 0


class CommunityChallenge(BaseModel):
    id: str
    name: str
    description: str
    participating_blocks: List[str]
    leaderboard: Dict[str, int]  # block_id -> total_points
