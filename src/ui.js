let ready;
let PIXELS_WIDTH, PIXELS_HEIGHT;
let pixelsCanvas;
let pz;

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
  const r = await performApiRequest(state, "get_size");
  const { width, height } = await r.json();
  PIXELS_WIDTH = width;
  PIXELS_HEIGHT = height;
  console.log(`Canvas is ${width}x${height} pixels`);

  // setup image
  pixelsCanvas = createImage(width, height);
  pixelsCanvas.loadPixels();
  for (let x = 0; x < pixelsCanvas.width; x++) {
    for (let y = 0; y < pixelsCanvas.height; y++) {
      pixelsCanvas.set(x, y, color(255, 0, 0));
    }
  }
  pixelsCanvas.updatePixels();

  // setup panzoom
  pz = panZoom();
  pz.setup(width, height);

  ready = true;
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

function mouseDragged() {
  if (!ready) return;
  pz.mouseDragged();
}

function mouseWheel(e) {
  if (!ready) return;
  pz.mouseWheel(e);
}

function draw() {
  background(0);
  if (!ready) return;

  pz.drawImage(pixelsCanvas);
}
