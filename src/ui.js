let ready;
let PIXELS_WIDTH, PIXELS_HEIGHT;
let pixelsCanvas;

let w, h, tow, toh;
let x, y, tox, toy;
const zoom = 0.01; //zoom step per mouse tick

async function setup() {
  createCanvas(windowWidth, windowHeight);

  // Setup client
  let state = getState();
  if (!state) {
    const token = prompt("Enter token:");
    if (!token) return null;
    state = genState(token);
    setState(state);
  }

  // Get canvas size
  console.log("Getting size...");
  // get_size is not ratelimited :)
  //const r = await performApiRequest(state, "get_size");
  //const { width, height } = await r.json();
  PIXELS_WIDTH = 1000;
  PIXELS_HEIGHT = 2000;
  console.log(`Canvas is ${PIXELS_WIDTH}x${PIXELS_HEIGHT} pixels`);

  // setup image
  pixelsCanvas = createImage(PIXELS_WIDTH, PIXELS_HEIGHT);
  pixelsCanvas.loadPixels();
  for (let x = 0; x < pixelsCanvas.width; x++) {
    for (let y = 0; y < pixelsCanvas.height; y++) {
      pixelsCanvas.set(x, y, color(255, 0, 0));
    }
  }
  pixelsCanvas.updatePixels();

  w = tow = pixelsCanvas.width;
  h = toh = pixelsCanvas.height;
  x = tox = w / 2;
  y = toy = h / 2;

  ready = true;
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

function mouseDragged() {
  if (!ready) return;
  tox += mouseX - pmouseX;
  toy += mouseY - pmouseY;
}

function mouseWheel(ev) {
  if (!ready) return;

  var e = -ev.delta;

  if (e > 0) {
    //zoom in
    for (var i = 0; i < e; i++) {
      if (tow > 30 * width) return; //max zoom
      tox -= zoom * (mouseX - tox);
      toy -= zoom * (mouseY - toy);
      tow *= zoom + 1;
      toh *= zoom + 1;
    }
  }

  if (e < 0) {
    //zoom out
    for (var i = 0; i < -e; i++) {
      if (tow < width) return; //min zoom
      tox += (zoom / (zoom + 1)) * (mouseX - tox);
      toy += (zoom / (zoom + 1)) * (mouseY - toy);
      toh /= zoom + 1;
      tow /= zoom + 1;
    }
  }
}

function draw() {
  background(0);
  if (!ready) return;

  //tween/smooth motion
  const tweenAmt = 0.1;
  x = lerp(x, tox, tweenAmt);
  y = lerp(y, toy, tweenAmt);
  w = lerp(w, tow, tweenAmt);
  h = lerp(h, toh, tweenAmt);

  image(pixelsCanvas, x - w / 2, y - h / 2, w, h);
}
