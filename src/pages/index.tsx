import { RGB } from "pixel-grid";
import PixelGrid from "../components/pixel-grid";

function Index() {
  /*const [data] = useState(() =>
    Array(64 * 3)
      .fill(0)
      .map(() => Math.floor(Math.random() * 255))
      .reduce((all, one, i) => {
        const ch = Math.floor(i / 3);
        all[ch] = [].concat(all[ch] || [], one);
        return all;
      }, [])
  );*/
  const r: RGB = [255, 0, 0];
  const g: RGB = [0, 255, 0];
  const b: RGB = [0, 0, 255];
  const x: RGB = [0, 0, 0];
  // prettier-ignore
  const data = [ 
    x, r, x, g, x, b,
    r, x, g, x, b, x,
    x, r, x, g, x, b,
    r, x, g, x, b, x,
    x, r, x, g, x, b,
    r, x, g, x, b, x,
  ];
  console.log(data);
  return <PixelGrid data={data} />;
}

export default Index;
