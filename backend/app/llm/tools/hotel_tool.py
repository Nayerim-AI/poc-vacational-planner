from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass
class Hotel:
    id: str
    name: str
    city: str
    price_per_night: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    rating: Optional[float] = None


class HotelTool(Protocol):
    """Hotel search abstraction to allow swapping providers."""

    def search_hotels(self, city: str, limit: int = 5) -> List[Hotel]:
        ...
