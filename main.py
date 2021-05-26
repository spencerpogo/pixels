from os import environ
import asyncio
import pickle
import logging
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

    def bad_pixels(self):
        w, h = self.im.size
        good = 0
        bad = 0
        for y in range(0, h):
            for x in range(0, w):
                if self.canvas.getpixel((self.x + x, self.y + y)) == self.im.getpixel(
                    (x, y)
                ):
                    good += 1
                else:
                    bad += 1
        if good + bad != w * h:
            raise ValueError("wtf")
        return good, good + bad

    def print_progress(self):
        good, total = self.bad_pixels()
        percent = (good / total) * 100
        print(f"Progress: {good} / {total} ({percent:.2g}%)")

    async def get_canvas(self):
        data = await self.client.get_pixels()
        self.save()
        im = Image.frombytes("RGB", self.size, data)
        self.canvas = im

    async def canvas_and_progress(self):
        await self.get_canvas()
        self.canvas.save("test.png")
        self.print_progress()

    async def canvas_thread(self):
        while True:
            await asyncio.sleep(5)
            await self.canvas_and_progress()

    def find_loc(self):
        w, h = self.im.size
        cx = w // 2
        cy = h // 2
        # Find pixels closest to center first
        for yoff in range(h):
            y = cy + (1 if yoff % 2 == 0 else -1) * yoff // 2
            for xoff in range(w):
                x = cx + (1 if xoff % 2 == 0 else -1) * xoff // 2
                if self.canvas.getpixel((self.x + x, self.y + y)) != self.im.getpixel(
                    (x, y)
                ):
                    return x, y
        # done
        raise ValueError("done")

    async def place_thread(self):
        while True:
            x, y = self.find_loc()
            pix = self.im.getpixel((x, y))
            await self.client.set_pixel(self.x + x, self.y + y, rgb_to_hex(pix))
            self.canvas.putpixel((x, y), pix)
            self.save()


async def main():
    logging.basicConfig(level=logging.INFO)
    args = sys.argv[1:]
    if len(args) < 3:
        print(f"Usage: {sys.argv[0]} <x> <y> <image_url>", file=sys.stderr)
        sys.exit(1)
    [x, y, img_url] = args
    x = int(x)
    y = int(y)
    client = await get_client()
    async with client:
        async with client.sess.get(img_url) as r:
            await client._check_status(r)
            img = Image.open(BytesIO(await r.read())).convert("RGB")
        w, h = img.size
        print(f"Loaded image, {w}x{h} = {w * h} pixels")
        # await client.set_pixel(x + 5, y + 5, rgb_to_hex(img.getpixel((5, 5))))
        # save_client(client)
        worker = Worker(client, img, x, y)
        await worker.init()
        await worker.canvas_and_progress()
        asyncio.get_event_loop().create_task(worker.canvas_thread())
        await worker.place_thread()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
