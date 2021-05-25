declare module "pixel-grid" {
  type RGB = [number, number, number];
  export type Data = RGB[] | number[];

  export default class Pixels {
    frame: any;
    canvas: HTMLCanvasElement;

    constructor(
      data: Data,
      opts?: {
        // todo
        size?: number;
        root?: HTMLElement;
      }
    );

    update(data: Data);
  }
}
