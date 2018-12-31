import asyncio
import aiohttp
import logging
import time
from aiomultiprocess import Pool

async def get(url):
    session = aiohttp.ClientSession()
    response = await session.get(url)
    session.close()
    return response

async def request():
    url = 'https://jreese.sh'
    urls = [url for _ in range(5)]
    async with Pool() as pool:
        result = await pool.map(get, urls)
        return result

logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()
loop.run_until_complete(request())