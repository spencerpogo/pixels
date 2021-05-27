import asyncio
import pickle
from dataclasses import dataclass
import traceback
from time import time as now

from aiohttp import ClientSession

API = "https://pixels.pythondiscord.com"
CHURCH = "https://pixel-tasks.scoder12.repl.co"


@dataclass
class Ratelimit:
    remaining: int = 1
    reset_at: float = 0

    @classmethod
    def default(cls):
        return cls(remaining=1, reset_at=0)


class Client:
    __slots__ = ("token", "sess", "key", "ratelimits")

    def __init__(self, token, key):
        self.token = token
        self.key = key
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
        # no need to check for ratelimit or send headers
        async with self.sess.get(API + "/get_size") as r:
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
        return max(0, l.reset_at - now())

    async def wait_for_ratelimit(self, method):
        wait = self.time_till_next_request(method)
        if wait > 0:
            await asyncio.sleep(wait)

    def _update_ratelimit(self, r, method):
        remaining = int(r.headers["requests-remaining"])
        reset_after = float(r.headers["requests-reset"])
        reset_at = now() + reset_after
        l = Ratelimit(remaining=remaining, reset_at=reset_at)
        self.ratelimits[method] = l

    async def _set_pixel(self, x, y, rgb):
        async with self.sess.post(
            API + "/set_pixel",
            json={"x": x, "y": y, "rgb": rgb},
            headers=self.headers(),
        ) as r:
            await self._check_status(r)
            self._update_ratelimit(r, "set_pixel")
            j = await r.json()
            return j

    async def set_pixel(self, x, y, rgb):
        await self.wait_for_ratelimit("set_pixel")
        return await self._set_pixel(x, y, rgb)

    async def _get_pixels(self):
        async with self.sess.get(API + "/get_pixels", headers=self.headers()) as r:
            await self._check_status(r)
            self._update_ratelimit(r, "get_pixels")
            return await r.read()

    async def get_pixels(self):
        await self.wait_for_ratelimit("get_pixels")
        return await self._get_pixels()


PICKLE_FILENAME = "pixels.pickle"


def save_client(client):
    with open(PICKLE_FILENAME, "wb") as f:
        pickle.dump(client, f)


async def get_client():
    try:
        with open(PICKLE_FILENAME, "rb") as f:
            client = pickle.load(f)
    except FileNotFoundError:
        token = input(f"Enter your token from {API}/authorize > ")
        key = input(f"Enter your rick church API key> ")
        client = Client(token, key)
        save_client(client)
    return client


async def task_loop():
    client = await get_client()
    async with client:
        while True:
            print("Waiting for ratelimit...")
            while not client.can_make_request("set_pixel"):
                await asyncio.sleep(1)

            print("Getting task...")
            async with client.sess.post(
                CHURCH + f"/api/get_task?key={client.key}"
            ) as r:
                await client._check_status(r)
                data = await r.json()
                task = data["task"]
                if task is None:
                    print("No tasks...")
                    await asyncio.sleep(2)
                    continue

            project = task["project_title"]
            color = task["color"]
            x = task["x"]
            y = task["y"]
            print(f"Task from project {project}: Placing {color} at {x},{y}")
            await client.set_pixel(x, y, color)
            save_client(client)

            async with client.sess.post(
                CHURCH + f"/api/submit_task?key={client.key}", json=task
            ) as r:
                await client._check_status(r)
                print(await r.json())
            await asyncio.sleep(2)


async def main():
    while True:
        try:
            await task_loop()
        except:
            traceback.print_exc()
        await asyncio.sleep(5)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
