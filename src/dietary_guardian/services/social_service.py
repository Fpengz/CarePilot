import logfire
from typing import Any, cast
from dietary_guardian.models.social import BlockScore, CommunityChallenge

logfire_api = cast(Any, logfire)

class SocialService:
    def __init__(self):
        self.blocks: dict[str, BlockScore] = {}
        self.challenges: list[CommunityChallenge] = []

    def register_block(self, block_id: str, postal_code_prefix: str):
        if block_id not in self.blocks:
            self.blocks[block_id] = BlockScore(block_id=block_id, postal_code_prefix=postal_code_prefix)
            logfire_api.info("block_registered", block_id=block_id)
        return self.blocks[block_id]

    def record_healthy_choice(self, block_id: str, choice_type: str):
        if block_id in self.blocks:
            block = self.blocks[block_id]
            if choice_type == "low_sugar":
                block.sugar_reduction_points += 10
            elif choice_type == "low_sodium":
                block.sodium_reduction_points += 10
            block.active_residents += 1
            logfire_api.info("healthy_choice_recorded", block_id=block_id, type=choice_type)


    def get_leaderboard(self, challenge_id: str) -> list[tuple[str, int]]:
        # For demo purposes, we return a sorted list of blocks by total points
        scores = [
            (b.block_id, b.sugar_reduction_points + b.sodium_reduction_points)
            for b in self.blocks.values()
        ]
        return sorted(scores, key=lambda x: x[1], reverse=True)
