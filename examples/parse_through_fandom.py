"""
parse_through_fandom.py: Page through an entire fandom through Atlas. Based on an example written by Iris.
"""

import asyncio
import json

import aiohttp

import src.atlas_api as atlas_api


# Import the authorization credentials from a config file. Note: This way of storing them isn't strictly necessary, but
# this wrapper doesn't come with the authorization credentials.
with open("../config.json", encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = tuple(info["atlas"])  # Or atlas_auth = ("login", "password")


async def parse_through_fandom():
    """Gets the ids, titles, and descriptions for all fics in a given fandom, as well as their total count."""

    # Use the fandom name as a search parameter for FFN works. Other possible search parameters include the title,
    # description, and author id of works.
    fandom_name = "Chronicles of Narnia"
    print(f"Getting information about fanfics in this fandom: {fandom_name}")

    # Create a ClientSession in order to close it gracefully. Not strictly necessary, since the atlas client can create
    # its own session if it's used as an async context manager (i.e. async with).
    async with aiohttp.ClientSession() as session:
        client = atlas_api.AtlasClient(auth=atlas_auth, session=session)

        # Keep track of the page (of size 10000, per the API) and fic counts, as well as the first fic id for each page.
        total_pages, total_fics, min_fic_id = 0, 0, 0

        while True:
            # Get the first 10000 fics with this fandom name, starting from a certain fic id.
            block = await client.get_bulk_metadata(min_fic_id=min_fic_id, raw_fandoms_ilike=fandom_name)
            total_fics += len(block)

            # No more fics to find in this fandom.
            if len(block) < 1:
                break

            total_pages += 1

            for fic in block:
                print(f"{fic.id}: {fic.title}")
                print(f"    {fic.description}\n")

            # Search for more fics using larger, uncovered fic ids as starting points.
            min_fic_id = max((fic.id for fic in block)) + 1

        print(f"Done in {total_pages=}: {total_fics=}")

    print("Exiting now...")
    await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(parse_through_fandom())
