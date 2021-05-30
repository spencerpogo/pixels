import base64
from typing import Optional
from io import BytesIO
from os import environ
import pickle
from collections import deque
from threading import Thread
import time
import random

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
from replit import db
import numpy as np

from client import Client

app = FastAPI()
PICKLE_FILENAME = "pixels.pickle"

bootup = time.time()
tasks = {}
workers = {}


def save_client(client):
    with open(PICKLE_FILENAME, "wb") as f:
        pickle.dump(client, f)


def load_client():
    try:
        with open(PICKLE_FILENAME, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        client = Client(environ["TOKEN"])
        save_client(client)
        return client


client = load_client()
canvas = None
last_progess_line = "Loading..."


def is_pixel_good(canvas, im, project, x, y):
    if im.mode == "RGBA":
        r, g, b, a = im.getpixel((x, y))
        if a == 0:
            return True
    elif im.mode == "RGB":
        r, g, b = im.getpixel((x, y))
    else:
        raise ValueError(f"Bad image mode {im.mode!r}")
    is_worm = rgb_to_hex((r, g, b)).upper() == "FF8983"
    return is_worm or (r, g, b) == canvas.getpixel((project.x + x, project.y + y))


def get_percent(project, canvas):
    im = deserialize_img(project.image)
    w, h = im.size
    # -- NUMPY OPTIMIZATIONS --
    target_area = canvas.crop((project.x, project.y, project.x + w, project.y + h))
    #if np.array_equal(np.asarray(target_area), np.asarray(im)):
        #return 100
    # -- END NUMPY OPTIMIZATIONS --

    good = 0
    bad = 0
    for y in range(0, h):
        for x in range(0, w):
            is_good = is_pixel_good(canvas, im, project, x, y)
            if is_good:
                good += 1
            else:
                bad += 1
    total = good + bad
    if total != w * h:
        raise ValueError(
            "Bruh the fuck this is almost as bad as 'IhaveSomeFunSometimes.js'"
        )
    percent = (good / total) * 100
    return percent


def print_progress(project, oldcanvas, canvas):
    return

    im = deserialize_img(project.image)
    w, h = im.size
    new_events = []
    good = 0
    bad = 0
    worm = 0
    for y in range(0, h):
        for x in range(0, w):
            canx = project.x + x
            cany = project.y + y
            is_good = is_pixel_good(canvas, im, project, x, y)

            if oldcanvas is not None:
                old = oldcanvas.getpixel((canx, cany))
                new = canvas.getpixel((canx, cany))
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
    global last_progress_line
    last_progress_line = f"\033[1m \033[92m PROGRESS REPORT: \033[0m{project.title} progress: {good} / {total} {percent:.2f}% {worm} worm {new_text}"
    print(last_progress_line)


def get_canvas():
    global canvas
    while True:
        size = client.get_size()
        data = client.get_pixels()
        save_client(client)
        canvas = Image.frombytes("RGB", size, data)
        canvas.save("./static/images/test.png")
        time.sleep(2)

def checkProgress():
    return

    global canvas
    while canvas is None:
        time.sleep(2)

    lastcanvas = None
    while True:
        lastcanvas = canvas
        for project in db.get("projects", {}).values():
            p = Project.parse_obj(project)
            print_progress(p, lastcanvas, canvas)
        time.sleep(240)

def expire_tasks_forever():
    global tasks
    while True:
        now = time.time()
        tasks = {key: t for key, t in tasks.items() if now - t.start < 10}
        time.sleep(2)


@app.on_event("startup")
def startup():
    Thread(target=get_canvas).start()
    Thread(target=checkProgress).start()
    Thread(target=expire_tasks_forever).start()


def deserialize_img(data):
    return Image.open(BytesIO(base64.b64decode(data)))



def serialize_img(img):
    f = BytesIO()
    img.save(f, format="PNG")
    return base64.b64encode(f.getvalue()).decode()


class Project(BaseModel):
    title: str
    x: int
    y: int
    image: str


class Task(BaseModel):
    start: float
    project_title: str
    x: int
    y: int
    color: str


def rgb_to_hex(pixel):
    return "{:02x}{:02x}{:02x}".format(*pixel)


# middleware, in fastapi this is called a dependency
# see create_project for example usage
def api_key(key: str) -> str:
    keys = db.get("keys", {})
    user = keys.get(key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return key, user


@app.post("/api/projects/delete")
def delete_Project(title, user=Depends(api_key)):
    """
    This is an **priest(admin) only end-point.**
    """
    key, name = user
    if name != "scoder12":
        raise HTTPException(
            status_code=401, detail="Delete project is currently limited to admins"
        )
    projects = db.get("projects", {})
    if title not in projects:
        raise HTTPException(status_code=409, detail="Project doesn't exists")
    new = {}
    print(projects)
    for proj in projects:
        if title != proj:
            new[proj] = projects[proj]
    db.set("projects", new)
    return {"ok": True}


@app.get("/api/user/stats")
def user_stats(user=Depends(api_key)):
  key, name = user
  completed = db.get("completed", {})
  v = completed[key] = completed.get(key, 0) + 1
  return {"username": name, "goodTasks": v}
  

@app.post("/api/projects/edit")
def edit_project(project: Project, user=Depends(api_key)):
    """
    This is an **priest(admin) only end-point**.

    - **title**: title of the project
    - **x**: x coordinate where the top left corner should be
    - **y**: y coordinate where the top left corner should be
    - **image**: Image base64 encoded
    """
    key, name = user
    if name != "scoder12":
        raise HTTPException(
            status_code=401, detail="Edit Project is currently limited to admins"
        )

    img = deserialize_img(project.image)
    cw, ch = client.get_size()
    w, h = img.size
    if w > cw or h > ch:
        raise HTTPException(
            status_code=400, detail=f"Image too large: {w}x{h} but max is {cw}x{ch}"
        )

    p = Project(title=project.title, x=project.x, y=project.y, image=serialize_img(img))
    projects = db.get("projects", {})
    if project.title not in projects:
        raise HTTPException(status_code=409, detail="Project doesn't exists")
    new = {}
    for proj in projects:
        if p.title == proj:
            new[proj] = p.dict()
        else:
            new[proj] = projects[proj]
    print(new)
    db.set("projects", new)
    return {"ok": True}


@app.post("/api/projects/create")
def create_project(project: Project, user=Depends(api_key)):
    """
    This is an **priest(admin) only end-point**.

    - **title**: title of the project
    - **x**: x coordinate where the top left corner should be
    - **y**: y coordinate where the top left corner should be
    - **image**: Image base64 encoded
    """
    key, name = user
    print(name)
    if name != "scoder12":
        raise HTTPException(
            status_code=401, detail="Create project is currently limited to admins"
        )

    img = deserialize_img(project.image)
    cw, ch = client.get_size()
    w, h = img.size
    if w > cw or h > ch:
        raise HTTPException(
            status_code=400, detail=f"Image too large: {w}x{h} but max is {cw}x{ch}"
        )

    # save the converted image to save space
    p = Project(title=project.title, x=project.x, y=project.y, image=serialize_img(img))
    projects = db.get("projects", {})
    if project.title in projects:
        raise HTTPException(status_code=409, detail="Project already exists")
    print(p)
    projects[project.title] = p.dict()
    return {"ok": True, "project": p}


class ProjectStats(BaseModel):
    name: str
    percent: str
    image: str
    x: int
    y: int


@app.get("/api/projects/stats")
def get_project_stats():
    projects = db.get("projects", {})
    r = []
    for project in projects.values():
        p = Project.parse_obj(project)
        r.append(
            ProjectStats(
                name=p.title,
                percent=f"{get_percent(p, canvas):.2f}",
                image=p.image,
                x=p.x,
                y=p.y,
            )
        )
    return list(reversed(r))


def task_exists(x, y):
    for t in tasks.values():
        if t.x == x and t.y == y:
            return True
    return False


def get_task() -> Project:
    while canvas is None:
        time.sleep(0.5)

    projects = db.get("projects", {})
    if not len("projects"):
        return None

    for o in projects.values():
        project = Project.parse_obj(o)
        img = deserialize_img(project.image)
        im_rgb = img.convert("RGB")
        w, h = img.size
        target_area = canvas.crop((project.x, project.y, project.x + w, project.y + h))
        if np.array_equal(np.asarray(target_area), np.asarray(im)):
            return 100

        total_pixels = w * h
        checked = set()

        while len(checked) < total_pixels:
            x = random.randint(0, w - 1)
            y = random.randint(0, h - 1)
            if (x, y) in checked:
                continue
            checked.add((x, y))

            cx = project.x + x
            cy = project.y + y
            imp = im_rgb.getpixel((x, y))
            if not is_pixel_good(canvas, img, project, x, y) and not task_exists(
                cx, cy
            ):
                return Task(
                    start=time.time(),
                    project_title=project.title,
                    x=cx,
                    y=cy,
                    color=rgb_to_hex(imp),
                )
    return None


@app.api_route("/api/get_task", methods=["GET", "POST"])
def api_get_task(user=Depends(api_key)):
    key, name = user
    if key in tasks:
        del tasks[key]

    task = get_task()
    print(f"Assigned {task} to {name}")
    if task is None:
        return {"task": None}

    # print(f"Assigning {task} to {name}")
    tasks[key] = task
    return {"task": task}


@app.get("/api/overall_stats")
def overall_stats():
    global workers
    projects = db.get("projects", {})
    now = time.time()
    workers = {key: t for key, t in workers.items() if now - t < 2 * 60}
    return {"projects": len(projects), "workers": len(workers)}


@app.get("/api/leaderboard")
def leaderboard():
    keys = db.get("keys", {})
    leaderboard = []

    for key, v in db.get("completed", {}).items():
        if key in keys:
          name = keys[key]
          leaderboard.append({"name": name, "tasks": v})

    return {
        "leaderboard": sorted(leaderboard, key=lambda i: i["tasks"], reverse=True),
        "uptime": time.time() - bootup,
    }


def validate_task(task):
    projects = db.get("projects", {})
    if task.project_title not in projects:
        raise HTTPException(status_code=500, detail="Invalid task")
    project = Project.parse_obj(projects[task.project_title])
    x = task.x - project.x
    y = task.y - project.y
    im = deserialize_img(project.image)
    is_valid = lambda: is_pixel_good(canvas, im, project, x, y)
    # print(canvas.getpixel((task.x, task.y)), im.getpixel((x, y)))

    if is_valid():
        return True
    time.sleep(3)
    return is_valid()

@app.post("/api/submit_task",  
      responses={
        200: {
          "description": "Submitted Task",
          "content": {
            "application/json": {
                "example": {
                  "ok": True,
                  "message": "Thank you for your service to rick!",
                  "completed": 1
                }
            }
          }
        },
        429: {
          "description": "Error with submitting task",
          "content": {
            "application/json": {
              "example": {
                "detail": "You have not gotten a task yet or you took more than 10 seconds to submit your task"
              }
            }
          }
        },
        409: {
          "description": "Not assigned task",
          "content": {
            "application/json": {
              "example": {
                "detail": "This is not the task you were assigned"
              }
            }
          }
        }
    }
  )
def submit_task(task: Task, user=Depends(api_key)):
    global workers
    key, name = user
    if key not in tasks:
        raise HTTPException(
            status_code=429,
            detail="You have not gotten a task yet or you took more than 10 seconds to submit your task",
        )
    t = tasks[key]
    if task != t:
        raise HTTPException(
            status_code=409, detail="This is not the task you were assigned"
        )

    del tasks[key]
    if not validate_task(task):
        raise HTTPException(
            status_code=400,
            detail="You did not complete this task properly, or it was fixed before the server could verify it. You have not been credited for this task.",
        )

    print(
        f"\n\u001b[32m{name} completed a task for project {task.project_title}\u001b[0m\n"
    )
    completed = db.get("completed", {})
    v = completed[key] = completed.get(key, 0) + 1
    workers[key] = time.time()

    return {
        "ok": True,
        "message": f"Thank you for your service to rick!",
        "completed": v,
    }


app.mount("/", StaticFiles(directory="static", html=True))
