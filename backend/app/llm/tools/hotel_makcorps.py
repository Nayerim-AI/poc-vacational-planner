import logging
from typing import List

import requests

from app.llm.tools.hotel_tool import Hotel, HotelTool

logger = logging.getLogger(__name__)


class MakCorpsHotelTool(HotelTool):
    """
    HotelTool implementation using MakCorps Free API.
    Requires JWT token from MakCorps (set via env/config).
    """

    def __init__(self, jwt_token: str):
        self.jwt_token = jwt_token

    def search_hotels(self, city: str, limit: int = 5) -> List[Hotel]:
        url = f"https://api.makcorps.com/free/{city}"
        headers = {"Authorization": f"JWT {self.jwt_token}"}

        try:
            resp = requests.get(url, headers=headers, timeout=8)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("MakCorps API request failed: %s", exc)
            return []

        data = resp.json() if resp.content else {}
        raw_hotels = data.get("hotels", [])

        hotels: List[Hotel] = []
        for h in raw_hotels[:limit]:
            price = h.get("lowest_price")
            try:
                price_val = float(price) if price is not None else None
            except (TypeError, ValueError):
                price_val = None

            hotel_id = h.get("hotel_name", "unknown").lower().replace(" ", "_")
            hotels.append(
                Hotel(
                    id=hotel_id,
                    name=h.get("hotel_name", "Unknown Hotel"),
                    city=city,
                    lat=None,
                    lon=None,
                    price_per_night=price_val or 0.0,
                    rating=None,
                )
            )

        return hotels
