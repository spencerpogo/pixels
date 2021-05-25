import Pixels, { Data } from "pixel-grid";
import React, { MutableRefObject, useEffect, useRef } from "react";

export default function PixelGrid({
  data = [],
  options = {},
  ...props
}: {
  data: Data;
  options?: {
    size?: number;
  };
}) {
  const grid: MutableRefObject<Pixels | null> = useRef(null);
  const container = useRef();
  const queue = useRef([]);

  useEffect(() => {
    grid.current = new Pixels(data, {
      ...options,
      root: container.current,
    });

    return () => {
      queue.current = [];
      grid.current.canvas && grid.current.canvas.remove();
    };
  }, [...Object.values(options), data.length]);

  useEffect(() => {
    setTimeout(() => {
      grid.current.frame &&
        grid.current.frame(() => {
          const shifted = queue.current.shift();
          shifted && grid.current.update(shifted);
        });
    }, 0);
  }, []);

  useEffect(() => {
    if (queue.current.length > 30) {
      console.warn("PixelGrid update queue > 30; flushing");
      queue.current = [];
    }
    queue.current.push(data);
  });

  return <div ref={container} {...props} />;
}
