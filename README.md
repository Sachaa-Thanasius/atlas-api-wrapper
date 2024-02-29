# Atlas API Wrapper
A small asynchronous wrapper for Iris's Atlas API, made to retrieve story metadata from FanFiction.Net (or FFN).

Note: The authentication credentials necessary to actually access the API aren't included. For those, talk to [Iris](https://github.com/iridescent-beacon). For a description of the API being wrapped, see Iris's OpenAPI-style specification [here](https://redocly.github.io/redoc/?url=https://atlas.fanfic.dev/openapi.yaml).


## Installing
**atlas-api-wrapper currently requires Python 3.8 or higher.**

To install the library, run one of the following commands:

```shell
# Linux/macOS
python3 -m pip install -U git+https://github.com/Sachaa-Thanasius/atlas-api-wrapper

# Windows
py -3 -m pip install -U git+https://github.com/Sachaa-Thanasius/atlas-api-wrapper
```


## Documentation
See the docstrings in the source code.


## Example
For more examples, see the [examples folder](https://github.com/Sachaa-Thanasius/atlas-api-wrapper/examples).

```python
import asyncio
import aiohttp
import atlas_api as atlas

async def main():
    async with aiohttp.ClientSession() as session:
        client = atlas.Client(
            session=session,
            auth=aiohttp.BasicAuth("login", "password")
        )
        url = "https://www.fanfiction.net/s/13912800/1/Magical-Marvel"
        story_metadata = await client.get_story_metadata(atlas.extract_fic_id(url))
        print(
            f"Story Metadata (link: '{story_metadata.url}')\n",
            f"    {story_metadata.id}: {story_metadata.title}\n",
            f"        {story_metadata.description}\n"
        )

asyncio.run(main())
```
