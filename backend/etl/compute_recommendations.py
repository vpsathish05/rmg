"""
Manual trigger for recommendation pre-compute.

Usage (from backend/ directory):
    PYTHONPATH=. python -m etl.compute_recommendations
"""
import asyncio
import logging
import sys
import os

# Load .env from backend root
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)

from app.database import SessionLocal
from app.services import rec_cache


async def main():
    print("Starting recommendation pre-compute…")
    print("This scores every 'Not Resourced' pipeline role with AI rationale + KB proofs.")
    print("Expected time: ~5–10 minutes depending on open roles.\n")

    db = SessionLocal()
    try:
        result = await rec_cache.compute_all(db)
        print(f"\nDone! {result['done']}/{result['total']} roles scored "
              f"({result['errors']} errors, {result['elapsed_seconds']}s elapsed)")
        if result["errors"] > 0:
            print("Check logs above for error details.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
