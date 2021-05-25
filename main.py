from os import environ
import asyncio
import pickle
import logging

from client import Client

logger = logging.getLogger()


CLIENT_PICKLE_FILENAME = "client.pkl"


class ClientPickler:
    __slots__ = ("client", "filename")

    def __init__(self, client, filename):
        self.client = client
        self.filename = filename

    def __enter__(self):
        return self

    def __exit__(self, *e):
        logging.debug("Writing client pickle")
        with open(self.filename, "wb") as f:
            pickle.dump(self.client, f)


def save(client):
    return ClientPickler(client, CLIENT_PICKLE_FILENAME)


async def main():
    logging.basicConfig(level=logging.DEBUG)
    logger.debug("Starting")

    try:
        with open(CLIENT_PICKLE_FILENAME, "rb") as f:
            client = pickle.load(f)
        logging.debug("Loaded pickled client")
    except FileNotFoundError:
        token = environ["TOKEN"]
        client = Client(token)
        logging.debug("Created new client")
        with save(client):
            pass

    async with client:
        with save(client):
            canvas = await client.get_pixels()

        with open("canvas.bin", "wb") as f:
            f.write(canvas)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
