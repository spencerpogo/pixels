from aiohttp import web, ClientSession

app = web.Application()
routes = web.RouteTableDef()

API_URL = "https://pixels.pythondiscord.com"


@routes.get("/")
async def index(req: web.Request) -> web.Response:
    # This is inefficient but doesn't require a restart to see changes
    return web.FileResponse("index.html")


app.add_routes(routes)


if __name__ == "__main__":
    web.run_app(app)
