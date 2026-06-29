import { Composition } from "remotion";
import { AiEngineVideo } from "./Video";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Video"
        component={AiEngineVideo}
        durationInFrames={1800}
        width={1920}
        height={1080}
        fps={30}
        defaultProps={{}}
      />
    </>
  );
};
