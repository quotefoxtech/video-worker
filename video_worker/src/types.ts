export type TextAnimation =
  | "slideUp"
  | "wordPop"
  | "typewriter"
  | "letterDrop"
  | "highlight"
  | "blurIn"
  | "glowReveal"
  | "gradientWave";

export type SceneType =
  | "title"
  | "bullets"
  | "imageGrid"
  | "flow"
  | "chart"
  | "timeline"
  | "checklist"
  | "stat"
  | "quote"
  | "comparison"
  | "bento"
  | "splitHero"
  | "outro";

export type Step = {title: string; detail?: string};
export type ChartPoint = {label: string; value: number; detail?: string};
export type TimelineEvent = {label: string; title: string; detail?: string};
export type ChecklistItem = {title: string; detail?: string};

export type Scene = {
  id: string;
  type: SceneType;
  textAnimation?: TextAnimation;
  narration?: string;
  /** image prompts (generation-time only, renderer ignores) */
  imagePrompts?: string[];
  /** resolved public-relative asset paths (injected by make_video.py) */
  audio?: string;
  images?: string[];
  // title / outro / splitHero
  title?: string;
  subtitle?: string;
  badge?: string;
  cta?: string;
  // bullets / general heading
  heading?: string;
  bullets?: string[];
  // imageGrid
  captions?: string[];
  // flow
  steps?: Step[];
  // chart
  data?: ChartPoint[];
  suffix?: string;
  // timeline
  timeline?: TimelineEvent[];
  // checklist
  items?: ChecklistItem[];
  // stat
  value?: number;
  label?: string;
  // quote
  quote?: string;
  attribution?: string;
  // comparison
  leftLabel?: string;
  leftItems?: string[];
  rightLabel?: string;
  rightItems?: string[];
  // bento
  heroTitle?: string;
  heroDetail?: string;
  statValue?: string | number;
  statLabel?: string;
  featureTitle?: string;
  featureDetail?: string;
};

export type Style = {
  bgFrom: string;
  bgTo: string;
  accent: string;
  textColor: string;
  mutedColor: string;
};

export type Script = {
  topic: string;
  slug: string;
  style: Style;
  scenes: Scene[];
};

export type ScriptProps = {
  script: Script;
  timings?: number[];
};
