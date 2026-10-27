"""Analytics, metrics, and statistical insights package."""
from .metrics import (
    calculate_team_summary_metrics,
    calculate_player_summary_metrics,
    calculate_match_margin_metrics,
    calculate_event_summary_metrics,
    calculate_head_to_head
)

__all__ = [
    "calculate_team_summary_metrics",
    "calculate_player_summary_metrics",
    "calculate_match_margin_metrics",
    "calculate_event_summary_metrics",
    "calculate_head_to_head"
]
