import asyncio
import pickle
import os
from dataclasses import dataclass
import traceback
from colorama import Fore
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

# For Stats
good = 0
bad = 0
totalTasks = 0
goodOverall = 0
curSesTotal = 0

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
        global bad
        if r.status != 200:
            try:
                text = await r.json()
                bad += 1
                de = text['detail']
                return print("["+Fore.RED + "-" + Fore.RESET + "] " + f"Error: {de}")
            except:
                text = traceback.format_exc()
                return print(f"Unexpected status {r.status}")

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
        token = input("["+Fore.CYAN + "i" + Fore.RESET + "] " + f"Enter your token from {API}/authorize > ")
        key = input("["+Fore.CYAN + "i" + Fore.RESET + "] " + f"Enter your rick church API key> ")
        client = Client(token, key)
        save_client(client)
    return client


async def task_loop():
    client = await get_client()
    async with client:
        global totalTasks
        global goodOverall
        global bad
        global good
        global curSesTotal
        username = ""
        async with client.sess.get(CHURCH + f"/api/user/stats?key={client.key}") as r:
            da = await r.json()
            goodOverall = da["goodTasks"]
            username = da["username"]
        while True:
            # clear the console
            os.system('cls' if os.name == 'nt' else 'clear')
            totalTasks = goodOverall + bad
            if bad >= 1:
                percent = (good/bad)*100
            else:
                percent = 100.00 
            if percent > 100.00:
                percent = 100.00
            curSesTotal = good + bad
            print("\033[1m" + f"Welcome {username},".center(os.get_terminal_size().columns))
            print(f"You've sumitted {totalTasks} good tasks over all time!".center(os.get_terminal_size().columns))
            print(f"Within the current session, you've submitted {curSesTotal} total tasks, {percent}% of them being good!".center(os.get_terminal_size().columns))
            print("["+ Fore.CYAN + "i" + Fore.RESET+ "] " + "Waiting for ratelimit...")
            while not client.can_make_request("set_pixel"):
                await asyncio.sleep(1)

            print("[" + Fore.CYAN + "i" + Fore.RESET+ "] " + "Getting task...")
            async with client.sess.get(
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
            print("["+Fore.GREEN + "+" + Fore.RESET + "] " + Fore.MAGENTA + f"Task from project" + "\033[94m" +f" {project}" + "\033[0m" + Fore.RESET + "\033[1m"+f": Placing {color} at {x},{y}")
            await client.set_pixel(x, y, color)
            save_client(client)

            async with client.sess.post(
                CHURCH + f"/api/submit_task?key={client.key}", json=task
            ) as r:
                await client._check_status(r)
                jsonRes = await r.json()
                if "ok" in jsonRes:
                    if jsonRes["ok"] == True:
                        goodOverall = jsonRes["completed"]
                        good += 1
                        print("["+Fore.GREEN + "+" + Fore.RESET + "] " + Fore.MAGENTA + f"Successfully submitted another Task!" + Fore.RESET + f" You've submitted {good} tasks!" + Fore.RESET)
                    else:
                        bad += 1
                        print("["+Fore.RED + "-" + Fore.RESET + "] " + f"Failed to submit a task!" + Fore.RESET)
                else:
                    bad += 1
                    print("["+Fore.RED + "-" + Fore.RESET + "] " + f"Failed to submit a task!" + Fore.RESET)
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
