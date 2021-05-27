from os import environ
import asyncio
import pickle
import logging
import random
import sys
from io import BytesIO

from PIL import Image

from client import Client

logger = logging.getLogger()


PICKLE_FILENAME = "pixels.pickle"


def save_client(client):
    with open(PICKLE_FILENAME, "wb") as f:
        pickle.dump(client, f)


async def get_client():
    try:
        with open(PICKLE_FILENAME, "rb") as f:
            client = pickle.load(f)
        logging.debug("Loaded pickled client")
    except FileNotFoundError:
        token = environ["TOKEN"]
        client = Client(token)
        logging.debug("Created new client")
        save_client(client)
    return client


def rgb_to_hex(pixel):
    return "{:02x}{:02x}{:02x}".format(*pixel)


class Worker:
    __slots__ = ("client", "im", "x", "y", "canvas", "size")

    def __init__(self, client, im, x, y):
        self.client = client
        self.im = im
        self.x = x
        self.y = y
        self.canvas = None
        self.size = None

    async def init(self):
        self.size = await self.client.get_size()

    def save(self):
        save_client(self.client)

    def is_loc_good(self, canvas, x, y):
        return canvas.getpixel((self.x + x, self.y + y)) == self.im.getpixel((x, y))

    def good_pixels(self):
        w, h = self.im.size
        good = 0
        bad = 0
        for y in range(0, h):
            for x in range(0, w):
                if self.is_loc_good(self.canvas, x, y):
                    good += 1
                else:
                    bad += 1
        if good + bad != w * h:
            raise ValueError("wtf")
        return good, good + bad

    def print_progress(self, oldcanvas):
        w, h = self.im.size
        new_events = []
        good = 0
        bad = 0
        for y in range(0, h):
            for x in range(0, w):
                is_good = self.is_loc_good(self.canvas, x, y)
                canx = self.x + x
                cany = self.y + y

                if oldcanvas is not None:
                    old = oldcanvas.getpixel((canx, cany))
                    new = self.canvas.getpixel((canx, cany))
                    if old != new:
                        status = "\u001b[32massist" if is_good else "\u001b[31mattack"
                        new_events.append(
                            f"{status} @ {canx},{cany} {rgb_to_hex(old)}->{rgb_to_hex(new)}\u001b[0m"
                        )
                if is_good:
                    good += 1
                else:
                    bad += 1
        if good + bad != w * h:
            raise ValueError("wtf")
        total = good + bad

        percent = (good / total) * 100
        new_text = ", ".join(new_events) if len(new_events) else ""
        print(f"Progress: {good} / {total} {percent:.2g}% {new_text}")

    async def get_canvas(self):
        data = await self.client.get_pixels()
        self.save()
        im = Image.frombytes("RGB", self.size, data)
        self.canvas = im

    async def canvas_and_progress(self):
        oldcanvas = self.canvas
        await self.get_canvas()
        self.canvas.save("test.png")
        self.print_progress(oldcanvas)

    async def canvas_thread(self):
        while True:
            await asyncio.sleep(2)
            await self.canvas_and_progress()

    def find_loc(self):
        w, h = self.im.size
        total_pixels = w * h
        checked = set()
        while len(checked) != total_pixels:
            x = random.randint(0, w - 1)
            y = random.randint(0, h - 1)
            canl = (self.x + x, self.y + y)
            if (x, y) in checked:
                continue
            now = self.canvas.getpixel(canl)
            target = self.im.getpixel((x, y))
            if now != target:
                return (*canl, target)
            checked.add((x, y))
        return None

    async def place_thread(self):
        while True:
            # Don't find loc till we can place
            while not self.client.can_make_request("set_pixel"):
                await asyncio.sleep(1)
            l = self.find_loc()
            if l is None:
                print("nothing to do, waiting")
                await asyncio.sleep(5)
                continue
            x, y, pix = l
            print(
                f"Placing: ({x},{y}) {rgb_to_hex(self.canvas.getpixel((x, y)))}->{rgb_to_hex(pix)}",
            )
            await self.client.set_pixel(x, y, rgb_to_hex(pix))
            self.canvas.putpixel((x, y), pix)
            self.save()


async def download_image(client, img_url):
    async with client.sess.get(img_url) as r:
        await client._check_status(r)
        return Image.open(BytesIO(await r.read())).convert("RGB")


async def main():
    logging.basicConfig(level=logging.INFO)
    args = sys.argv[1:]
    if len(args) < 3:
        print(f"Usage: {sys.argv[0]} <x> <y> <image_url / img_path>", file=sys.stderr)
        sys.exit(1)
    [x, y, img_url] = args
    x = int(x)
    y = int(y)
    client = await get_client()
    async with client:
        if img_url.startswith("http://") or img_url.startswith("https://"):
            im = await download_image(client, img_url)
        else:
            im = Image.open(img_url)
        w, h = im.size
        print(f"Loaded image, {w}x{h} = {w * h} pixels")
        # await client.set_pixel(x + 5, y + 5, rgb_to_hex(img.getpixel((5, 5))))
        # save_client(client)
        worker = Worker(client, im, x, y)
        await worker.init()
        await worker.canvas_and_progress()
        asyncio.get_event_loop().create_task(worker.canvas_thread())
        await worker.place_thread()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
