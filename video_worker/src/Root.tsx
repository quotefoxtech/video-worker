import {Composition} from "remotion";
import {TopicVideo, calculateMetadata, defaultProps} from "./TopicVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="TopicVideo"
      component={TopicVideo}
      durationInFrames={60 * 30}
      fps={30}
      width={1280}
      height={720}
      defaultProps={defaultProps}
      calculateMetadata={calculateMetadata}
    />
  );
};
