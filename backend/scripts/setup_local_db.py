import asyncio

import asyncpg


async def main():
    try:
        conn = await asyncpg.connect(
            user="postgres",
            password="okay",
            host="localhost",
            port=5432,
            database="postgres",
        )
        print("[OK] Connected to PostgreSQL as user 'postgres'")

        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'gap'")
        if not exists:
            await conn.execute("CREATE DATABASE gap")
            print("[OK] Created database 'gap'")
        else:
            print("[OK] Database 'gap' already exists")
        await conn.close()

        conn_gap = await asyncpg.connect(
            user="postgres",
            password="okay",
            host="localhost",
            port=5432,
            database="gap",
        )
        try:
            await conn_gap.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("[OK] Extension 'vector' enabled")
        except Exception as e:
            print(f"[NOTE] pgvector extension: {e}")
        await conn_gap.close()
        print("[OK] Database setup completed successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
