# Copyright 2018 John Reese
# Licensed under the MIT license

import asyncio
import logging
import os
import sys

from unittest import TestCase

import aiomultiprocess as amp

from .base import async_test

log = logging.getLogger()


def init():
    hdl = logging.StreamHandler(sys.stderr)
    log = logging.getLogger()
    log.addHandler(hdl)
    # log.setLevel(logging.DEBUG)
    # amp.core.log.setLevel(logging.DEBUG)


async def two():
    return 2


async def sleepypid(t=0.1):
    await asyncio.sleep(t)
    return os.getpid()


async def mapper(value):
    return value * 2


async def starmapper(*values):
    return [value * 2 for value in values]


class CoreTest(TestCase):
    @classmethod
    def setUpClass(cls):
        init()

    def setUp(self):
        amp.set_context("spawn")

    @async_test
    async def test_process(self):
        p = amp.Process(target=sleepypid, name="test_process")
        p.start()

        self.assertEqual(p.name, "test_process")
        self.assertTrue(p.pid)
        self.assertTrue(p.is_alive())

        await p.join()
        self.assertFalse(p.is_alive())

    @async_test
    async def test_process_timeout(self):
        p = amp.Process(target=sleepypid, args=(1,))
        p.start()

        with self.assertRaises(asyncio.TimeoutError):
            await p.join(timeout=0.01)

    @async_test
    async def test_worker(self):
        p = amp.Worker(target=sleepypid)
        p.start()
        await p.join()

        self.assertFalse(p.is_alive())
        self.assertEqual(p.result, p.pid)

    @async_test
    async def test_worker_join(self):
        # test results from join
        p = amp.Worker(target=sleepypid)
        p.start()
        self.assertEqual(await p.join(), p.pid)

        # test awaiting p directly, no need to start
        p = amp.Worker(target=sleepypid)
        self.assertEqual(await p, p.pid)

    @async_test
    async def test_pool_worker(self):
        tx = amp.core.context.Queue()
        rx = amp.core.context.Queue()
        worker = amp.core.PoolWorker(tx, rx, 1)
        worker.start()

        self.assertTrue(worker.is_alive())
        tx.put_nowait((1, mapper, (5,), {}))
        await asyncio.sleep(0.5)
        result = rx.get_nowait()

        self.assertEqual(result, (1, 10))
        self.assertFalse(worker.is_alive())  # maxtasks == 1

    @async_test
    async def test_pool(self):
        values = list(range(10))
        results = [await mapper(i) for i in values]

        async with amp.Pool(2) as pool:
            await asyncio.sleep(0.5)
            self.assertEqual(pool.process_count, 2)
            self.assertEqual(len(pool.processes), 2)

            self.assertEqual(await pool.apply(mapper, (values[0],)), results[0])
            self.assertEqual(await pool.map(mapper, values), results)
            self.assertEqual(
                await pool.starmap(starmapper, [values[:4], values[4:]]),
                [results[:4], results[4:]],
            )

    @async_test
    async def test_spawn_context(self):
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

        log.debug("testing bad context")
        with self.assertRaises(ValueError):
            amp.set_context("foo")

        async def inline(x):
            return x

        log.debug("testing good context")
        amp.set_context("spawn")

        log.debug("testing spawn + inline function")
        with self.assertRaises(AttributeError):
            p = amp.Worker(
                target=inline, args=(1,), name="test_inline", initializer=init
            )
            p.start()
            await p.join()

        log.debug("testing spawn + global function")
        p = amp.Worker(target=two, name="test_global", initializer=init)
        p.start()
        await p.join()

        log.debug("testing spawn + pool.map")
        values = list(range(10))
        results = [await mapper(i) for i in values]
        async with amp.Pool(2, initializer=init) as pool:
            self.assertEqual(await pool.map(mapper, values), results)

        self.assertEqual(p.result, 2)
