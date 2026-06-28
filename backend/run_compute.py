"""Run compute_all with full logging to see what's failing."""
import asyncio
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

from app.database import SessionLocal
from app.services.rec_cache import compute_all

async def main():
    db = SessionLocal()
    try:
        result = await compute_all(db)
        print(f"\n{'='*50}")
        print(f"RESULT: {result}")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

asyncio.run(main())
