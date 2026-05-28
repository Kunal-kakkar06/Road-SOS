import os
import asyncio
from database import engine, Base, AsyncSessionLocal
from models.blackspot_model import AccidentBlackspot
from sqlalchemy import delete

SPOTS = [
    {"lat":12.9716,"lng":77.5946,"road":"MG Road","area":"Central","accidents":45,"fatal":8,"cause":"signal_jumping","intensity":0.9,"risk":"critical"},
    {"lat":12.9352,"lng":77.6245,"road":"Silk Board Junction","area":"Koramangala","accidents":62,"fatal":12,"cause":"congestion","intensity":1.0,"risk":"critical"},
    {"lat":13.0358,"lng":77.5970,"road":"Hebbal Flyover","area":"Hebbal","accidents":38,"fatal":6,"cause":"speeding","intensity":0.8,"risk":"high"},
    {"lat":12.9698,"lng":77.7499,"road":"ITPL Main Road","area":"Whitefield","accidents":29,"fatal":4,"cause":"pothole","intensity":0.65,"risk":"high"},
    {"lat":12.9141,"lng":77.6101,"road":"BTM Layout","area":"BTM","accidents":31,"fatal":3,"cause":"pedestrian","intensity":0.7,"risk":"high"},
    {"lat":13.0100,"lng":77.5509,"road":"Yeshwantpur Junction","area":"Yeshwantpur","accidents":41,"fatal":7,"cause":"signal_jumping","intensity":0.85,"risk":"critical"},
    {"lat":12.9259,"lng":77.5760,"road":"Bannerghatta Road","area":"JP Nagar","accidents":27,"fatal":3,"cause":"speeding","intensity":0.60,"risk":"medium"},
    {"lat":13.0456,"lng":77.6200,"road":"Outer Ring Road","area":"Marathahalli","accidents":55,"fatal":9,"cause":"speeding","intensity":0.92,"risk":"critical"},
    {"lat":12.9592,"lng":77.6974,"road":"Varthur Road","area":"Marathahalli","accidents":33,"fatal":5,"cause":"pothole","intensity":0.72,"risk":"high"},
    {"lat":12.9847,"lng":77.7057,"road":"Old Airport Road","area":"Kodihalli","accidents":22,"fatal":4,"cause":"speeding","intensity":0.55,"risk":"medium"},
    {"lat":12.9766,"lng":77.5713,"road":"Raj Bhavan Road","area":"Vasanth Nagar","accidents":18,"fatal":2,"cause":"overspeeding","intensity":0.45,"risk":"medium"},
    {"lat":12.9001,"lng":77.6476,"road":"HSR Layout","area":"HSR","accidents":19,"fatal":2,"cause":"pothole","intensity":0.42,"risk":"medium"},
]

async def seed():
    # Make sure all tables are created on startup first
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Detect SQLite
    is_sqlite = "sqlite" in os.getenv("DATABASE_URL", "")

    # Set up geography location if not SQLite and GeoAlchemy2 is installed
    from_shape = None
    Point = None
    if not is_sqlite:
        try:
            from geoalchemy2.shape import from_shape
            from shapely.geometry import Point
        except ImportError:
            pass

    async with AsyncSessionLocal() as db:
        try:
            await db.execute(delete(AccidentBlackspot))
            await db.commit()
        except Exception as e:
            print(f"Skipping clean delete: {e}")
            await db.rollback()

        for s in SPOTS:
            spot = AccidentBlackspot(
                latitude=s["lat"],
                longitude=s["lng"],
                road_name=s["road"],
                area_name=s["area"],
                total_accidents=s["accidents"],
                fatal_accidents=s["fatal"],
                primary_cause=s["cause"],
                intensity=s["intensity"],
                risk_level=s["risk"],
                year=2023,
            )
            if from_shape and Point:
                spot.location = from_shape(Point(s["lng"], s["lat"]), srid=4326)

            db.add(spot)
        await db.commit()
    print(f"Seeded {len(SPOTS)} blackspots successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
