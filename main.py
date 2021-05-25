from os import getenv
from typing import Callable

from aiohttp import web, ClientSession

app = web.Application()
routes = web.RouteTableDef()

IS_PROD = getenv("PYTHON_ENV", "").lower().startswith("prod")
API_URL = "https://pixels.pythondiscord.com"


@routes.get("/")
async def index(req: web.Request) -> web.Response:
    # This is inefficient but doesn't require a restart to see changes
    return web.FileResponse("index.html")


@routes.view("/api/{endpoint}")
async def api_proxy(req: web.Request) -> web.Response:
    async with ClientSession() as sess:
        url = API_URL + "/" + req.match_info["endpoint"]
        print(req.method, url)
        reqheaders = req.headers.copy()  # make mutable
        del reqheaders["host"]
        reqheaders["user-agent"] = "pixels/0.1.0; https://github.com/Scoder12/pixels"
        async with sess.request(
            req.method,
            url,
            headers=reqheaders,
            params=req.rel_url.query,
            data=await req.read(),
        ) as res:
            resheaders = res.headers.copy()  # make mutable
            resheaders["access-control-allow-origin"] = "*"
            return web.Response(
                body=await res.read(), status=res.status, headers=resheaders
            )


app.add_routes(routes)


if __name__ == "__main__":
    web.run_app(app)
