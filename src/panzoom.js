//Based on Zoom/Pan Component
//by Rick Companje, Nov 1, 2018.
//https://gist.github.com/companje/5478fff07a18a1f4806df4cf77ae1048

function panZoom() {
  const zoom = 0.01; //zoom step per mouse tick

  let w, h, tow, toh;
  let x, y, tox, toy;

  function setup(width, height) {
    w = tow = width;
    h = toh = height;
    x = tox = w / 2;
    y = toy = h / 2;
  }

  function drawImage(img) {
    //tween/smooth motion
    x = lerp(x, tox, 0.1);
    y = lerp(y, toy, 0.1);
    w = lerp(w, tow, 0.1);
    h = lerp(h, toh, 0.1);

    image(img, x - w / 2, y - h / 2, w, h);
  }

  function mouseDragged() {
    tox += mouseX - pmouseX;
    toy += mouseY - pmouseY;
  }

  function mouseWheel(event) {
    var e = -event.delta;

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

  return { setup, drawImage, mouseDragged, mouseWheel };
}
