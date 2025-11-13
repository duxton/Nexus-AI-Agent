from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import time

class OutletInfo(BaseModel):
    name: str
    location: str
    area: str
    opening_time: str
    closing_time: str
    phone: Optional[str] = None
    address: Optional[str] = None

# Sample outlet data
OUTLETS_DATA: Dict[str, List[OutletInfo]] = {
    "petaling_jaya": [
        OutletInfo(
            name="SS 2 Outlet",
            location="SS 2",
            area="Petaling Jaya",
            opening_time="9:00 AM",
            closing_time="10:00 PM",
            phone="+603-7876-5432",
            address="No. 15, Jalan SS 2/24, SS 2, 47300 Petaling Jaya, Selangor"
        ),
        OutletInfo(
            name="SS 15 Outlet",
            location="SS 15",
            area="Petaling Jaya",
            opening_time="8:30 AM",
            closing_time="9:30 PM",
            phone="+603-7876-1234",
            address="No. 8, Jalan SS 15/3A, SS 15, 47500 Petaling Jaya, Selangor"
        ),
        OutletInfo(
            name="Damansara Utama Outlet",
            location="Damansara Utama",
            area="Petaling Jaya",
            opening_time="10:00 AM",
            closing_time="11:00 PM",
            phone="+603-7726-8888",
            address="G-12, Damansara Utama, 47400 Petaling Jaya, Selangor"
        )
    ],
    "kuala_lumpur": [
        OutletInfo(
            name="KLCC Outlet",
            location="KLCC",
            area="Kuala Lumpur",
            opening_time="10:00 AM",
            closing_time="10:00 PM",
            phone="+603-2161-9999",
            address="Level 2, Suria KLCC, 50088 Kuala Lumpur"
        ),
        OutletInfo(
            name="Bukit Bintang Outlet",
            location="Bukit Bintang",
            area="Kuala Lumpur",
            opening_time="11:00 AM",
            closing_time="11:30 PM",
            phone="+603-2148-7777",
            address="Lot 10 Shopping Centre, 50 Jalan Sultan Ismail, 50250 Kuala Lumpur"
        )
    ]
}

class OutletService:
    def __init__(self):
        self.outlets = OUTLETS_DATA

    def find_outlets_by_area(self, area: str) -> List[OutletInfo]:
        area_key = area.lower().replace(" ", "_")
        return self.outlets.get(area_key, [])

    def find_outlet_by_location(self, area: str, location: str) -> Optional[OutletInfo]:
        outlets = self.find_outlets_by_area(area)
        for outlet in outlets:
            if location.lower() in outlet.location.lower():
                return outlet
        return None

    def search_outlets(self, query: str) -> List[OutletInfo]:
        results = []
        query_lower = query.lower()

        for area_outlets in self.outlets.values():
            for outlet in area_outlets:
                if (query_lower in outlet.name.lower() or
                    query_lower in outlet.location.lower() or
                    query_lower in outlet.area.lower()):
                    results.append(outlet)

        return results

    def get_all_areas(self) -> List[str]:
        return [area.replace("_", " ").title() for area in self.outlets.keys()]

# Global outlet service instance
outlet_service = OutletService()