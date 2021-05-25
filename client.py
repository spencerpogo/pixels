import asyncio
from dataclasses import dataclass
import traceback
import logging
from time import time as now
import pickle

from aiohttp import ClientSession


API = "https://pixels.pythondiscord.com"

logger = logging.getLogger(__name__)


@dataclass
class Ratelimit:
    remaining: int = 1
    reset_at: float = 0

    @classmethod
    def default(cls):
        return cls(remaining=1, reset_at=0)


class Client:
    __slots__ = ("token", "sess", "ratelimits")

    def __init__(self, token):
        self.token = token
        self.sess = None
        self.ratelimits = {}

    async def __aenter__(self):
        self.sess = ClientSession()
        return self

    async def __aexit__(self, *args):
        await self.sess.close()

    def __getstate__(self):
        return {a: getattr(self, a) for a in self.__slots__ if a != "sess"}

    def __setstate__(self, state):
        for a, v in state.items():
            setattr(self, a, v)

    def headers(self):
        return {"authorization": f"Bearer {self.token}"}

    async def _check_status(self, r):
        if r.status != 200:
            try:
                text = repr(await r.text())
            except:
                text = traceback.format_exc()
            raise ValueError(f"Unexpected status {r.status} {text}")

    async def get_size(self) -> (int, int):
        # no need to check for ratelimit
        async with self.sess.get(API + "/get_size", headers=self.headers()) as r:
            await self._check_status(r)
            data = await r.json()
            return int(data["width"]), int(data["height"])

    def get_ratelimit(self, method):
        l = self.ratelimits.get(method)
        if l is None:
            return Ratelimit.default()
        return l

    def can_make_request(self, method):
        l = self.get_ratelimit(method)
        if l.remaining > 0:
            return True
        return now() >= l.reset_at

    def time_till_next_request(self, method):
        l = self.get_ratelimit(method)
        if l.remaining > 0:
            return 0
        return max(0, now() - l.reset_at)

    async def wait_for_ratelimit(self, method):
        wait = self.time_till_next_request(method)
        logging.debug(f"Waiting for {wait}")
        if wait > 0:
            await asyncio.sleep(wait)

    def _update_ratelimit(self, r, method):
        remaining = int(r.headers["requests-remaining"])
        reset_after = float(r.headers["requests-reset"])
        reset_at = now() + reset_after
        l = Ratelimit(remaining=remaining, reset_at=reset_at)
        self.ratelimits[method] = l
        logging.debug(
            f"{method} ratelimit: {l.remaining} remaining, reset after {reset_after}s"
        )

    async def _set_pixel(self, x, y, rgb):
        logger.info(f"Placing {rgb} @ {x},{y}")
        async with self.sess.post(
            API + "/set_pixel",
            json={"x": x, "y": y, "rgb": rgb},
            headers=self.headers(),
        ) as r:
            await self.check_status(r)
            self._update_ratelimit(r, "set_pixel")
            j = await r.json()
            logging.debug(f"set_pixel response: {j!r}")
            return j

    async def set_pixel(self, x, y, rgb):
        await self.wait_for_ratelimit("set_pixel")
        return await self._set_pixel(x, y, rgb)

    async def _get_pixels(self):
        logger.info("Reading canvas...")
        async with self.sess.get(API + "/get_pixels", headers=self.headers()) as r:
            await self._check_status(r)
            self._update_ratelimit(r, "get_pixels")
            return await r.read()

    async def get_pixels(self):
        await self.wait_for_ratelimit("get_pixels")
        return await self._get_pixels()
