"""
Build Knowledge Base — embed all projects into project_embeddings.

Run: PYTHONPATH=. python -m etl.build_kb
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.services.kb import build_all


async def main():
    db = SessionLocal()
    try:
        print("Building Knowledge Base…")
        n = await build_all(db)
        print(f"Done. {n} project embeddings created.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
