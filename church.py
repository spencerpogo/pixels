import asyncio
from main import get_client, save_client


async def main():
    client = await get_client()
    async with client:
        while True:
            # Get the command from thy holy god.
            print("Getting task...")
            async with client.sess.get("https://decorator-factory.su/tasks") as r:
                data = await r.json()
                latest_task = data[0]
                print(latest_task)
                tid = latest_task["id"]
                x = latest_task["x"]
                y = latest_task["y"]
                col = latest_task["color"]
            print(f"Starting task {tid}. Fill in {x},{y} with #{col}")
            await client.set_pixel(x, y, col)
            save_client(client)
            # await asyncio.sleep(5)
            async with client.sess.post(
                "https://decorator-factory.su/submit_task", json={"task_id": tid}
            ) as r:
                print(await r.json())


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
