"""
get_metadata_from_link.py: Get the metadata for a specific fic using its FFN url.
"""

import asyncio
import json

import aiohttp

from src.atlas_api import AtlasAPI


with open("../config.json", encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = tuple(info["atlas"])  # Or atlas_auth = ("login", "password")


async def get_metadata_from_link():
    """Gets the metadata for one work of fanfic with its url."""

    ffn_link = "https://www.fanfiction.net/s/13912800/1/Magical-Marvel"
    print("Getting metadata from this link: ", ffn_link)

    async with aiohttp.ClientSession() as session:
        atlas = AtlasAPI(auth=atlas_auth, session=session)
        print("Set up Atlas connection.")

        story_metadata = await atlas.get_story_metadata(atlas.extract_fic_id(ffn_link))
        print(f"FFN Specific Metadata:\n{story_metadata}")

    print("Gracefully ending now...")
    await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(get_metadata_from_link())
