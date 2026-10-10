"""Seed the database: `uv run python -m app.seed`."""

import asyncio

from app.db import SessionLocal, engine
from app.seed import load_glossary_seed, seed_glossary, seed_users


async def main() -> None:
    entries = load_glossary_seed()
    async with SessionLocal() as session:
        user_result = await seed_users(session)
        result = await seed_glossary(session, entries)
        await session.commit()
    await engine.dispose()

    print(f"Users: {user_result.created} created, {len(user_result.skipped)} already present")
    print(f"Glossary: {result.created} created, {len(result.skipped)} already present")


if __name__ == "__main__":
    asyncio.run(main())
