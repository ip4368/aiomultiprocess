import asyncio
import aiohttp
import logging
import time
from aiomultiprocess import core, Pool


async def get(url):
    session = aiohttp.ClientSession()
    response = await session.get(url)
    session.close()
    return await response


async def request():
    url = "https://jreese.sh"
    urls = [url for _ in range(5)]
    async with Pool() as pool:
        logging.debug("running pool.map()")
        result = await pool.map(get, urls)
        logging.debug("pool.map() completed")
        return result


def main():
    core.set_context("spawn")
    logging.basicConfig(level=logging.DEBUG)
    core.log.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(request())


if __name__ == "__main__":
    main()
