import React from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  staticFile,
} from "remotion";
import {Audio as MediaAudio} from "@remotion/media";
import {TransitionSeries, linearTiming} from "@remotion/transitions";
import {fade} from "@remotion/transitions/fade";
import {slide} from "@remotion/transitions/slide";
import {loadFont} from "@remotion/google-fonts/Poppins";
import {getAudioDuration} from "./get-audio-duration";
import {
  BentoScene,
  BulletsScene,
  ComparisonScene,
  FlowScene,
  ImageGridScene,
  OutroScene,
  QuoteScene,
  SceneChip,
  SplitHeroScene,
  StatScene,
  TitleScene,
} from "./scenes";
import {ChartScene, ChecklistScene, TimelineScene} from "./advanced-scenes";
import type {Scene, ScriptProps} from "./types";

const {fontFamily} = loadFont("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});

export const FPS = 30;
const TRANSITION_FRAMES = 13;
const PAD_SEC = 0.45;
const FALLBACK_SEC: Record<Scene["type"], number> = {
  title: 4.5,
  outro: 4.5,
  bullets: 7,
  imageGrid: 7,
  flow: 7,
  chart: 7,
  timeline: 7,
  checklist: 7,
  stat: 5,
  quote: 6,
  comparison: 7.5,
  bento: 7.5,
  splitHero: 7,
};

/** Studio fallback so the composition renders before any --props exist */
export const defaultProps: ScriptProps = {
  script: {
    topic: "Run  python make_video.py",
    slug: "placeholder",
    style: {
      bgFrom: "#0b1e3a",
      bgTo: "#142c55",
      accent: "#3ec1f0",
      textColor: "#ffffff",
      mutedColor: "#b0b8c8",
    },
    scenes: [
      {
        id: "placeholder",
        type: "title",
        title: "Run make_video.py",
        subtitle: "python make_video.py  →  enter a topic  →  get a video",
        badge: "AI VIDEO BOT",
        textAnimation: "wordPop",
      },
    ],
  },
};

export const calculateMetadata: CalculateMetadataFunction<ScriptProps> = async ({
  props,
}) => {
  const durations = await Promise.all(
    props.script.scenes.map(async (s) => {
      if (!s.audio) return FALLBACK_SEC[s.type];
      try {
        return await getAudioDuration(staticFile(s.audio));
      } catch {
        console.warn(`audio missing: ${s.audio} — using fallback duration`);
        return FALLBACK_SEC[s.type];
      }
    }),
  );
  const timings = durations.map((d) => Math.ceil((d + PAD_SEC) * FPS));
  const overlap =
    TRANSITION_FRAMES * Math.max(0, props.script.scenes.length - 1);
  const durationInFrames = timings.reduce((a, b) => a + b, 0) - overlap;
  console.log(
    `${props.script.topic}: ${props.script.scenes.length} scenes, ${(
      durationInFrames / FPS
    ).toFixed(1)}s`,
  );
  return {durationInFrames, props: {...props, timings}};
};

const SceneRouter: React.FC<{
  scene: Scene;
  style: ScriptProps["script"]["style"];
  dur: number;
  index: number;
  total: number;
}> = ({scene, style, dur, index, total}) => {
  const props = {scene, style, dur, index, total};
  switch (scene.type) {
    case "title":
      return <TitleScene {...props} />;
    case "bullets":
      return <BulletsScene {...props} />;
    case "imageGrid":
      return <ImageGridScene {...props} />;
    case "flow":
      return <FlowScene {...props} />;
    case "chart":
      return <ChartScene {...props} />;
    case "timeline":
      return <TimelineScene {...props} />;
    case "checklist":
      return <ChecklistScene {...props} />;
    case "stat":
      return <StatScene {...props} />;
    case "quote":
      return <QuoteScene {...props} />;
    case "comparison":
      return <ComparisonScene {...props} />;
    case "bento":
      return <BentoScene {...props} />;
    case "splitHero":
      return <SplitHeroScene {...props} />;
    case "outro":
      return <OutroScene {...props} />;
  }
};

export const TopicVideo: React.FC<ScriptProps> = ({script, timings}) => {
  const nodes: React.ReactNode[] = [];
  script.scenes.forEach((scene, i) => {
    const dur = timings?.[i] ?? FALLBACK_SEC[scene.type] * FPS;
    if (i > 0) {
      const isCard = scene.type === "title" || scene.type === "outro";
      nodes.push(
        <TransitionSeries.Transition
          key={`tr-${scene.id}`}
          presentation={isCard ? fade() : slide({direction: "from-right"})}
          timing={linearTiming({durationInFrames: TRANSITION_FRAMES})}
        />,
      );
    }
    nodes.push(
      <TransitionSeries.Sequence
        key={scene.id}
        durationInFrames={dur}
        style={{fontFamily}}
      >
        {scene.audio ? (
          <MediaAudio src={staticFile(scene.audio)} volume={0.92} />
        ) : null}
        <SceneRouter
          scene={scene}
          style={script.style}
          dur={dur}
          index={i}
          total={script.scenes.length}
        />
        <SceneChip
          index={i}
          total={script.scenes.length}
          accent={script.style.accent}
        />
      </TransitionSeries.Sequence>,
    );
  });
  return (
    <AbsoluteFill style={{backgroundColor: script.style.bgFrom || "#070b14"}}>
      <TransitionSeries>{nodes}</TransitionSeries>
    </AbsoluteFill>
  );
};
