#!/usr/bin/env python3
"""
ZUS Coffee Outlets Database Setup and Text2SQL Implementation
"""

import sqlite3
import os
from typing import List, Dict, Optional, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, time
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Outlet(Base):
    __tablename__ = 'outlets'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postcode = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    phone = Column(String(50))
    email = Column(String(100))
    opening_time = Column(String(20))
    closing_time = Column(String(20))
    is_24_hours = Column(Boolean, default=False)
    has_drive_thru = Column(Boolean, default=False)
    has_wifi = Column(Boolean, default=True)
    has_parking = Column(Boolean, default=True)
    services = Column(Text)  # JSON string of services
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postcode': self.postcode,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'phone': self.phone,
            'email': self.email,
            'opening_time': self.opening_time,
            'closing_time': self.closing_time,
            'is_24_hours': self.is_24_hours,
            'has_drive_thru': self.has_drive_thru,
            'has_wifi': self.has_wifi,
            'has_parking': self.has_parking,
            'services': json.loads(self.services) if self.services else []
        }


class OutletsDatabase:
    """Database manager for ZUS Coffee outlets"""

    def __init__(self, db_path: str = "data/outlets.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def populate_sample_data(self) -> None:
        """Populate database with sample ZUS Coffee outlet data"""
        sample_outlets = [
            {
                "name": "ZUS Coffee KLCC",
                "address": "Lot G-23A, Ground Floor, Suria KLCC, 50088 Kuala Lumpur",
                "city": "Kuala Lumpur",
                "state": "Federal Territory of Kuala Lumpur",
                "postcode": "50088",
                "latitude": 3.1570,
                "longitude": 101.7107,
                "phone": "+603-2382-2828",
                "email": "klcc@zuscoffee.com",
                "opening_time": "07:00",
                "closing_time": "22:00",
                "is_24_hours": False,
                "has_drive_thru": False,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway"]
            },
            {
                "name": "ZUS Coffee Bukit Bintang",
                "address": "Lot LG-40, Lower Ground Floor, Pavilion KL, 168 Jalan Bukit Bintang, 55100 Kuala Lumpur",
                "city": "Kuala Lumpur",
                "state": "Federal Territory of Kuala Lumpur",
                "postcode": "55100",
                "latitude": 3.1478,
                "longitude": 101.7147,
                "phone": "+603-2148-8888",
                "email": "pavilion@zuscoffee.com",
                "opening_time": "08:00",
                "closing_time": "23:00",
                "is_24_hours": False,
                "has_drive_thru": False,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "dine-in"]
            },
            {
                "name": "ZUS Coffee SS15 Subang",
                "address": "47-G, Jalan SS 15/4D, SS 15, 47500 Subang Jaya, Selangor",
                "city": "Subang Jaya",
                "state": "Selangor",
                "postcode": "47500",
                "latitude": 3.0738,
                "longitude": 101.5861,
                "phone": "+603-5634-5555",
                "email": "ss15@zuscoffee.com",
                "opening_time": "07:00",
                "closing_time": "21:00",
                "is_24_hours": False,
                "has_drive_thru": True,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "drive-thru", "delivery"]
            },
            {
                "name": "ZUS Coffee Damansara Utama",
                "address": "G-03, Ground Floor, Damansara Uptown, Jalan SS 21/37, Damansara Utama, 47400 Petaling Jaya, Selangor",
                "city": "Petaling Jaya",
                "state": "Selangor",
                "postcode": "47400",
                "latitude": 3.1359,
                "longitude": 101.6253,
                "phone": "+603-7733-9999",
                "email": "damansara@zuscoffee.com",
                "opening_time": "06:30",
                "closing_time": "22:30",
                "is_24_hours": False,
                "has_drive_thru": False,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "dine-in", "meetings"]
            },
            {
                "name": "ZUS Coffee KL Gateway",
                "address": "LG-18, Lower Ground Floor, KL Gateway Mall, No.2, Jalan Kerinchi, Bangsar South, 59200 Kuala Lumpur",
                "city": "Kuala Lumpur",
                "state": "Federal Territory of Kuala Lumpur",
                "postcode": "59200",
                "latitude": 3.1167,
                "longitude": 101.6692,
                "phone": "+603-2201-7777",
                "email": "klgateway@zuscoffee.com",
                "opening_time": "07:30",
                "closing_time": "21:30",
                "is_24_hours": False,
                "has_drive_thru": False,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "dine-in"]
            },
            {
                "name": "ZUS Coffee Sunway Pyramid",
                "address": "LG2.74A, Lower Ground 2, Sunway Pyramid, No. 3, Jalan PJS 11/15, Bandar Sunway, 47500 Subang Jaya, Selangor",
                "city": "Subang Jaya",
                "state": "Selangor",
                "postcode": "47500",
                "latitude": 3.0733,
                "longitude": 101.6067,
                "phone": "+603-7492-8888",
                "email": "sunway@zuscoffee.com",
                "opening_time": "08:00",
                "closing_time": "22:00",
                "is_24_hours": False,
                "has_drive_thru": False,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "dine-in", "student-friendly"]
            },
            {
                "name": "ZUS Coffee Setia Alam Drive Thru",
                "address": "No. 23, Persiaran Setia Dagang, Setia Alam, Seksyen U13, 40170 Shah Alam, Selangor",
                "city": "Shah Alam",
                "state": "Selangor",
                "postcode": "40170",
                "latitude": 3.1024,
                "longitude": 101.4444,
                "phone": "+603-3359-6666",
                "email": "setiaalam@zuscoffee.com",
                "opening_time": "06:00",
                "closing_time": "24:00",
                "is_24_hours": True,
                "has_drive_thru": True,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "drive-thru", "24-hours", "delivery"]
            },
            {
                "name": "ZUS Coffee IOI City Mall",
                "address": "L1-45, Level 1, IOI City Mall, Lebuh IRC, IOI Resort City, 62502 Putrajaya, Selangor",
                "city": "Putrajaya",
                "state": "Selangor",
                "postcode": "62502",
                "latitude": 2.9264,
                "longitude": 101.6964,
                "phone": "+603-8945-5555",
                "email": "ioicity@zuscoffee.com",
                "opening_time": "09:00",
                "closing_time": "22:00",
                "is_24_hours": False,
                "has_drive_thru": False,
                "has_wifi": True,
                "has_parking": True,
                "services": ["espresso", "cold brew", "pastries", "sandwiches", "wifi", "takeaway", "dine-in", "family-friendly"]
            }
        ]

        session = self.get_session()
        try:
            # Clear existing data
            session.query(Outlet).delete()

            # Insert sample data
            for outlet_data in sample_outlets:
                services_json = json.dumps(outlet_data.pop("services"))
                outlet = Outlet(**outlet_data, services=services_json)
                session.add(outlet)

            session.commit()
            print(f"✅ Populated database with {len(sample_outlets)} outlets")

        except Exception as e:
            session.rollback()
            print(f"❌ Error populating database: {e}")
        finally:
            session.close()

    def execute_query(self, sql_query: str) -> Tuple[List[Dict], str]:
        """Execute a SQL query and return results"""
        try:
            session = self.get_session()
            result = session.execute(sql_query)

            # Convert to list of dictionaries
            columns = result.keys() if hasattr(result, 'keys') else []
            rows = []

            for row in result:
                if hasattr(row, '_asdict'):
                    rows.append(row._asdict())
                elif hasattr(row, 'keys'):
                    rows.append(dict(row))
                else:
                    # Handle simple tuple results
                    if columns:
                        rows.append(dict(zip(columns, row)))
                    else:
                        rows.append({'result': row})

            session.close()
            return rows, "success"

        except Exception as e:
            return [], f"SQL Error: {str(e)}"


class Text2SQLEngine:
    """Text-to-SQL engine for outlet queries"""

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db = OutletsDatabase()

    def get_schema_info(self) -> str:
        """Get database schema information for prompt"""
        return """
Database Schema:
Table: outlets
Columns:
- id: INTEGER (Primary Key)
- name: VARCHAR(200) - Outlet name (e.g., 'ZUS Coffee KLCC')
- address: TEXT - Full address
- city: VARCHAR(100) - City name (e.g., 'Kuala Lumpur', 'Petaling Jaya')
- state: VARCHAR(100) - State name (e.g., 'Selangor', 'Federal Territory of Kuala Lumpur')
- postcode: VARCHAR(20) - Postal code
- latitude: FLOAT - GPS latitude
- longitude: FLOAT - GPS longitude
- phone: VARCHAR(50) - Phone number
- email: VARCHAR(100) - Email address
- opening_time: VARCHAR(20) - Opening time in HH:MM format
- closing_time: VARCHAR(20) - Closing time in HH:MM format
- is_24_hours: BOOLEAN - True if open 24 hours
- has_drive_thru: BOOLEAN - True if has drive-thru service
- has_wifi: BOOLEAN - True if has WiFi
- has_parking: BOOLEAN - True if has parking
- services: TEXT - JSON string of services (e.g., ["espresso", "cold brew", "pastries"])
- created_at: DATETIME - Record creation timestamp

Sample services include: espresso, cold brew, pastries, sandwiches, wifi, takeaway, drive-thru, dine-in, delivery, 24-hours, meetings, student-friendly, family-friendly
"""

    def natural_language_to_sql(self, nl_query: str) -> str:
        """Convert natural language query to SQL"""
        try:
            schema = self.get_schema_info()

            prompt = f"""You are an expert SQL generator for a ZUS Coffee outlets database.

{schema}

Convert this natural language question to a valid SQLite query:
"{nl_query}"

Rules:
1. Only generate SELECT statements (no INSERT, UPDATE, DELETE)
2. Use proper SQLite syntax
3. For time comparisons, use string comparison (e.g., opening_time <= '10:00')
4. For JSON services, use LIKE operator (e.g., services LIKE '%drive-thru%')
5. Use LIMIT clause for "first few", "top", etc.
6. Be case-insensitive where appropriate using LOWER()
7. Return only the SQL query, no explanation

Examples:
- "outlets in Kuala Lumpur" → SELECT * FROM outlets WHERE LOWER(city) = 'kuala lumpur'
- "outlets with drive thru" → SELECT * FROM outlets WHERE has_drive_thru = 1
- "24 hour outlets" → SELECT * FROM outlets WHERE is_24_hours = 1
- "outlets that serve pastries" → SELECT * FROM outlets WHERE services LIKE '%pastries%'

SQL Query:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Generate only valid SQLite SELECT queries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )

            sql_query = response.choices[0].message.content.strip()

            # Remove code block formatting if present
            if sql_query.startswith("```"):
                sql_query = sql_query.split('\n')[1:-1]
                sql_query = '\n'.join(sql_query)

            return sql_query

        except Exception as e:
            return f"-- Error generating SQL: {str(e)}"

    def query(self, nl_query: str) -> Dict:
        """Process natural language query and return results"""
        try:
            # Generate SQL
            sql_query = self.natural_language_to_sql(nl_query)

            if sql_query.startswith("-- Error"):
                return {
                    "sql_query": sql_query,
                    "results": [],
                    "error": "Failed to generate SQL query",
                    "success": False
                }

            # Execute SQL
            results, status = self.db.execute_query(sql_query)

            if status != "success":
                return {
                    "sql_query": sql_query,
                    "results": [],
                    "error": status,
                    "success": False
                }

            return {
                "sql_query": sql_query,
                "results": results,
                "count": len(results),
                "success": True
            }

        except Exception as e:
            return {
                "sql_query": "N/A",
                "results": [],
                "error": str(e),
                "success": False
            }


# Global instances
outlets_db = OutletsDatabase()
text2sql = Text2SQLEngine()


def initialize_outlets_db():
    """Initialize the outlets database"""
    print("Initializing outlets database...")
    outlets_db.populate_sample_data()
    print("✅ Outlets database initialized")


def main():
    """Test the outlets database and Text2SQL"""
    print("🏪 Testing Outlets Database & Text2SQL")

    # Initialize database
    initialize_outlets_db()

    # Test queries
    test_queries = [
        "Show all outlets in Kuala Lumpur",
        "Which outlets have drive-thru?",
        "Find 24-hour outlets",
        "Outlets in Selangor state",
        "Which outlets serve pastries?",
        "Show outlets with parking",
        "Find outlets that open before 7 AM"
    ]

    for query in test_queries:
        print(f"\n❓ Query: {query}")
        result = text2sql.query(query)

        if result["success"]:
            print(f"🔍 SQL: {result['sql_query']}")
            print(f"📊 Found {result['count']} results")

            # Show first few results
            for outlet in result["results"][:2]:
                if isinstance(outlet, dict) and 'name' in outlet:
                    print(f"   - {outlet['name']}")
        else:
            print(f"❌ Error: {result['error']}")


if __name__ == "__main__":
    main()