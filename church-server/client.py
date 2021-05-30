from dataclasses import dataclass
import traceback
import logging
from time import sleep, time as now

import requests


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
    __slots__ = ("token", "ratelimits")

    def __init__(self, token):
        self.token = token
        self.ratelimits = {}

    def __getstate__(self):
        return {a: getattr(self, a) for a in self.__slots__ if a != "sess"}

    def __setstate__(self, state):
        for a, v in state.items():
            setattr(self, a, v)

    def headers(self):
        return {"authorization": f"Bearer {self.token}"}

    def _check_status(self, r):
        if r.status_code != 200:
            try:
                text = repr(r.text)
            except:
                text = traceback.format_exc()
            raise ValueError(f"Unexpected status {r.status_code} {r.headers} {text}")

    def get_size(self) -> (int, int):
        # no need to check for ratelimit or send headers
        r = requests.get(API + "/get_size")
        self._check_status(r)
        data = r.json()
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

    def wait_for_ratelimit(self, method):
        wait = self.time_till_next_request(method)
        logging.debug(f"Waiting for {wait}")
        if wait > 0:
            sleep(wait)

    def _update_ratelimit(self, r, method):
        remaining = int(r.headers["requests-remaining"])
        reset_after = float(r.headers["requests-reset"])
        reset_at = now() + reset_after
        l = Ratelimit(remaining=remaining, reset_at=reset_at)
        self.ratelimits[method] = l
        logging.debug(
            f"{method} ratelimit: {l.remaining} remaining, reset after {reset_after}s"
        )

    def _set_pixel(self, x, y, rgb):
        logger.info(f"Placing {rgb} @ {x},{y}")
        r = requests.post(
            API + "/set_pixel",
            json={"x": x, "y": y, "rgb": rgb},
            headers=self.headers(),
        )
        self._check_status(r)
        self._update_ratelimit(r, "set_pixel")
        j = r.json()
        logging.info(f"set_pixel response: {j!r}")
        return j

    def set_pixel(self, x, y, rgb):
        self.wait_for_ratelimit("set_pixel")
        return self._set_pixel(x, y, rgb)

    def _get_pixels(self):
        logger.debug("Reading canvas...")
        r = requests.get(API + "/get_pixels", headers=self.headers())
        self._check_status(r)
        self._update_ratelimit(r, "get_pixels")
        return r.content

    def get_pixels(self):
        self.wait_for_ratelimit("get_pixels")
        return self._get_pixels()
