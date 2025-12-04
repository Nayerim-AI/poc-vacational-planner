from __future__ import annotations

from typing import Dict, List


class SearchTool:
    def __init__(self) -> None:
        self.catalog: Dict[str, dict] = {
            "Lisbon": {
                "flight": {"provider": "mock-air", "price": 450.0, "duration_hours": 4},
                "hotel": {"name": "Lisbon Central", "price_per_night": 160.0},
                "activities": [
                    {
                        "title": "Alfama walking tour",
                        "description": "Explore historic Lisbon on foot.",
                        "price": 60.0,
                        "booking_required": True,
                    },
                    {
                        "title": "LX Factory evening",
                        "description": "Food and art markets by the river.",
                        "price": 40.0,
                        "booking_required": False,
                    },
                ],
            },
            "Bali": {
                "flight": {"provider": "mock-air", "price": 900.0, "duration_hours": 16},
                "hotel": {"name": "Ubud Retreat", "price_per_night": 120.0},
                "activities": [
                    {
                        "title": "Rice terrace sunrise",
                        "description": "Guided sunrise hike to Tegallalang.",
                        "price": 80.0,
                        "booking_required": True,
                    },
                    {
                        "title": "Cooking class",
                        "description": "Learn Balinese cuisine with locals.",
                        "price": 55.0,
                        "booking_required": True,
                    },
                ],
            },
        }

    def has_destination(self, destination: str) -> bool:
        return destination in self.catalog

    def default_destination(self) -> str:
        return list(self.catalog.keys())[0]

    def lookup_destination(self, destination: str) -> dict:
        if destination not in self.catalog:
            return self.catalog[self.default_destination()]
        return self.catalog[destination]

    def destinations(self) -> List[str]:
        return list(self.catalog.keys())
