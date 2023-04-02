"""
parse_through_fandom.py: Page through an entire fandom through Atlas. Based on an example written by Iris.
"""

import asyncio
import json

from src.atlas_api import AtlasAPI


with open("../config.json", encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = tuple(info["atlas"])  # Or atlas_auth = ("login", "password")


async def parse_through_fandom():
    """Gets the ids, titles, and descriptions for all fics in a given fandom, as well as their total count."""

    fandom_name = "Chronicles of Narnia"
    print(f"Getting information about fanfics in this fandom: {fandom_name}")

    atlas = AtlasAPI(auth=atlas_auth)
    print("Set up Atlas connection.")

    total_pages, total_fics, min_fic_id = 0, 0, 0

    while True:
        block = await atlas.get_bulk_metadata(min_fic_id=min_fic_id, raw_fandoms_ilike=fandom_name)
        total_fics += len(block)

        if len(block) < 1:
            break

        total_pages += 1

        for fic in block:
            print(f"{fic.id:8}: {fic.title}")
            print(f"    {fic.description}\n")

        min_fic_id = max((fic.id for fic in block)) + 1

    print(f"Done in {total_pages=}: {total_fics=}")

    print("Gracefully ending now...")
    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(parse_through_fandom())
