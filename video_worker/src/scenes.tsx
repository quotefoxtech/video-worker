import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {AnimatedText} from "./AnimatedText";
import type {Scene, Style} from "./types";

const CLAMP = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;

export type SceneProps = {
  scene: Scene;
  style: Style;
  dur: number;
  index: number;
  total: number;
};

/**
 * Cinematic Motion Graphics Studio Background:
 * Clean, deep matte canvas + procedural animated SVG film grain
 * + architectural technical dot matrix + subtle vignette.
 * 100% free of cheap neon glows, flares, and tacky gradients.
 */
export const Background: React.FC<{style: Style}> = ({style}) => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2); // 15fps organic film grain cadence

  return (
    <AbsoluteFill
      style={{
        backgroundColor: style.bgFrom || "#080c14",
        overflow: "hidden",
      }}
    >
      {/* Architectural Precision Dot Matrix */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `radial-gradient(circle, rgba(255,255,255,0.065) 1.2px, transparent 1.2px)`,
          backgroundSize: "32px 32px",
          backgroundPosition: "0 0",
          opacity: 0.65,
          pointerEvents: "none",
        }}
      />

      {/* Procedural Animated SVG Film Grain (Gives clean analog cinema texture) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          opacity: 0.035,
          mixBlendMode: "overlay",
        }}
      >
        <svg
          style={{
            position: "absolute",
            width: "100%",
            height: "100%",
          }}
        >
          <filter id="cinematic-grain">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.85"
              numOctaves={3}
              seed={seed}
            />
            <feColorMatrix
              type="matrix"
              values="0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0 0 0 1 0"
            />
          </filter>
          <rect width="100%" height="100%" filter="url(#cinematic-grain)" />
        </svg>
      </div>

      {/* Subtle Cinematic Vignette */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 55%, rgba(0, 0, 0, 0.45) 85%, rgba(0, 0, 0, 0.75) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

/** Full-bleed image with cinematic dark overlay & continuous Ken Burns camera push */
export const BgImage: React.FC<{src?: string; style: Style}> = ({
  src,
  style,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const zoom = interpolate(
    frame,
    [0, durationInFrames],
    [1.00, 1.045],
    CLAMP,
  );
  const panX = interpolate(frame, [0, durationInFrames], [0, -12], CLAMP);

  if (!src) return <Background style={style} />;
  return (
    <AbsoluteFill style={{overflow: "hidden"}}>
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${zoom}) translate3d(${panX}px, 0, 0)`,
          filter: "brightness(0.68) contrast(1.08)",
        }}
      />
      <AbsoluteFill
        style={{
          backgroundColor: "rgba(6, 10, 18, 0.65)",
        }}
      />
    </AbsoluteFill>
  );
};

/** Modern Scene Counter Chip (e.g., "[ ● 02 / 07 ]") */
export const SceneChip: React.FC<{index: number; total: number; accent: string}> = ({
  index,
  total,
  accent,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: 32,
        right: 44,
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 20,
        fontWeight: 600,
        color: "#ffffff",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 999,
        padding: "8px 22px",
        background: "rgba(18, 24, 38, 0.8)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
        letterSpacing: "0.1em",
        zIndex: 50,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: accent,
        }}
      />
      <span>
        {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
      </span>
    </div>
  );
};

/** Premium Glass Card with clean borders, Ken Burns zoom, and subtle floating physics */
export const ImageCard: React.FC<{
  src: string;
  dur: number;
  delay?: number;
  kenburns?: boolean;
  style?: React.CSSProperties;
}> = ({src, dur, delay = 0, kenburns = true, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({
    frame,
    fps,
    delay: delay * fps,
    config: {damping: 20, mass: 0.7, stiffness: 125},
  });

  const zoom = interpolate(frame, [0, Math.max(dur, fps)], [1.00, 1.05], CLAMP);
  const hoverY = Math.sin((frame + delay * 10) / 32) * 4;

  return (
    <div
      style={{
        borderRadius: 22,
        overflow: "hidden",
        boxShadow: "0 20px 50px rgba(0,0,0,0.55)",
        border: "1px solid rgba(255,255,255,0.12)",
        background: "rgba(18, 24, 38, 0.72)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        opacity: entrance,
        transform: `translate3d(0, ${(1 - entrance) * 30 + hoverY}px, 0) scale(${0.92 + entrance * 0.08})`,
        willChange: "transform, opacity",
        ...style,
      }}
    >
      <Img
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: kenburns ? `scale(${zoom})` : undefined,
          display: "block",
        }}
      />
    </div>
  );
};

const glassCardStyle: React.CSSProperties = {
  background: "rgba(18, 24, 38, 0.72)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 20,
  boxShadow: "0 16px 40px -10px rgba(0,0,0,0.6)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
};

// ── 1. Title Scene ──────────────────────────────────────────────────────────

export const TitleScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const badgeEnter = spring({
    frame,
    fps,
    delay: fps * 0.1,
    config: {damping: 20, mass: 0.7},
  });

  return (
    <>
      <BgImage src={scene.images?.[0]} style={style} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          padding: "0 80px",
        }}
      >
        {scene.badge ? (
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              color: style.accent,
              border: "1px solid rgba(255,255,255,0.14)",
              background: "rgba(18, 24, 38, 0.85)",
              backdropFilter: "blur(16px)",
              WebkitBackdropFilter: "blur(16px)",
              borderRadius: 999,
              padding: "10px 28px",
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              marginBottom: 34,
              opacity: badgeEnter,
              transform: `translate3d(0, ${(1 - badgeEnter) * 20}px, 0) scale(${0.9 + badgeEnter * 0.1})`,
              boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: style.accent,
              }}
            />
            {scene.badge}
          </div>
        ) : null}

        <h1
          style={{
            margin: 0,
            fontSize: 90,
            fontWeight: 800,
            lineHeight: 1.1,
            maxWidth: 1080,
            letterSpacing: "-0.02em",
            textShadow: "0 4px 24px rgba(0,0,0,0.8)",
          }}
        >
          <AnimatedText
            text={scene.title ?? ""}
            animation={scene.textAnimation ?? "wordPop"}
            delay={0.25}
            accent={style.accent}
            style={{fontSize: 90, fontWeight: 800, color: style.textColor}}
          />
        </h1>

        {scene.subtitle ? (
          <h2
            style={{
              margin: "30px 0 0",
              fontSize: 34,
              fontWeight: 500,
              color: style.mutedColor,
              maxWidth: 900,
              lineHeight: 1.4,
              textShadow: "0 4px 20px rgba(0,0,0,0.6)",
            }}
          >
            <AnimatedText
              text={scene.subtitle}
              animation="slideUp"
              delay={0.9}
              accent={style.accent}
              style={{fontSize: 34, fontWeight: 500, color: style.mutedColor}}
            />
          </h2>
        ) : null}
      </AbsoluteFill>
    </>
  );
};

// ── 2. Bullets Scene ────────────────────────────────────────────────────────

export const BulletsScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const lineProgress = spring({
    frame,
    fps,
    config: {damping: 20, mass: 0.7},
    durationInFrames: Math.round(fps * 0.7),
  });

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "54px 76px", flexDirection: "column"}}>
        <h2 style={{margin: 0, color: style.accent, fontSize: 52, fontWeight: 700}}>
          <AnimatedText
            text={scene.heading ?? ""}
            animation={scene.textAnimation ?? "highlight"}
            delay={0.15}
            accent={style.accent}
            style={{fontSize: 52, fontWeight: 700, color: style.accent}}
          />
        </h2>

        {/* Solid Understated Divider Line */}
        <div
          style={{
            marginTop: 20,
            width: "100%",
            height: 2,
            background: "rgba(255,255,255,0.08)",
            borderRadius: 1,
            position: "relative",
          }}
        >
          <div
            style={{
              width: `${lineProgress * 100}%`,
              height: "100%",
              backgroundColor: style.accent,
              borderRadius: 1,
            }}
          />
        </div>

        <div
          style={{
            flex: 1,
            display: "flex",
            gap: 52,
            alignItems: "center",
            minHeight: 0,
            marginTop: 28,
          }}
        >
          {/* Bullets List */}
          <div
            style={{
              flex: 1.25,
              display: "flex",
              flexDirection: "column",
              gap: 22,
            }}
          >
            {scene.bullets?.map((b, i) => {
              const p = spring({
                frame,
                fps,
                delay: (0.5 + i * 0.45) * fps,
                config: {damping: 20, mass: 0.7},
              });

              return (
                <div
                  key={i}
                  style={{
                    ...glassCardStyle,
                    padding: "18px 24px",
                    display: "flex",
                    gap: 22,
                    alignItems: "center",
                    opacity: p,
                    transform: `translate3d(${(1 - p) * -45}px, 0, 0)`,
                  }}
                >
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: 14,
                      backgroundColor: style.accent,
                      color: "#050a14",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 24,
                      fontWeight: 800,
                      flexShrink: 0,
                    }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </div>

                  <AnimatedText
                    text={b}
                    animation="wordPop"
                    delay={0.6 + i * 0.45}
                    accent={style.accent}
                    style={{
                      fontSize: 34,
                      fontWeight: 600,
                      color: "#ffffff",
                      lineHeight: 1.3,
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* Right Image Card */}
          {scene.images?.[0] ? (
            <div style={{flex: 1, height: "100%", maxHeight: 450}}>
              <ImageCard
                src={scene.images[0]}
                dur={8 * fps}
                delay={0.4}
                style={{height: "100%", width: "100%"}}
              />
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </>
  );
};

// ── 3. Image Grid Scene ─────────────────────────────────────────────────────

export const ImageGridScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "50px 70px", flexDirection: "column"}}>
        <h2 style={{margin: "0 0 28px", textAlign: "center", fontSize: 50, fontWeight: 700}}>
          <AnimatedText
            text={scene.heading ?? ""}
            animation={scene.textAnimation ?? "blurIn"}
            delay={0.1}
            accent={style.accent}
            style={{fontSize: 50, fontWeight: 700, color: style.accent}}
          />
        </h2>

        {/* 3D Perspective Card Grid */}
        <div
          style={{
            flex: 1,
            display: "flex",
            gap: 32,
            alignItems: "stretch",
            minHeight: 0,
            perspective: 1200,
          }}
        >
          {scene.images?.slice(0, 3).map((img, i) => {
            const p = spring({
              frame,
              fps,
              delay: (0.35 + i * 0.28) * fps,
              config: {damping: 20, mass: 0.7},
            });

            const tilt = (i - 1) * -3;
            const floatY = Math.sin((frame + i * 15) / 26) * 6;

            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  gap: 16,
                  opacity: p,
                  transform: `translate3d(0, ${(1 - p) * 50 + floatY}px, 0) rotateY(${tilt}deg) scale(${0.85 + p * 0.15})`,
                  transformStyle: "preserve-3d",
                }}
              >
                <div style={{flex: 1, minHeight: 0, position: "relative"}}>
                  <ImageCard
                    src={img}
                    dur={10 * fps}
                    delay={0}
                    style={{width: "100%", height: "100%"}}
                  />
                </div>

                {scene.captions?.[i] ? (
                  <div
                    style={{
                      ...glassCardStyle,
                      padding: "12px 18px",
                      textAlign: "center",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                    }}
                  >
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        backgroundColor: style.accent,
                      }}
                    />
                    <AnimatedText
                      text={scene.captions[i]}
                      animation="slideUp"
                      delay={0.7 + i * 0.28}
                      accent={style.accent}
                      style={{
                        fontSize: 24,
                        fontWeight: 600,
                        color: "#f0f4fc",
                        lineHeight: 1.3,
                      }}
                    />
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </>
  );
};

// ── 4. Flow Scene (Step-by-Step) ────────────────────────────────────────────

export const FlowScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const steps = scene.steps ?? [];

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "50px 64px", flexDirection: "column"}}>
        <h2 style={{margin: "0 0 32px", textAlign: "center", fontSize: 50, fontWeight: 700}}>
          <AnimatedText
            text={scene.heading ?? ""}
            animation={scene.textAnimation ?? "letterDrop"}
            delay={0.1}
            accent={style.accent}
            style={{fontSize: 50, fontWeight: 700, color: style.accent}}
          />
        </h2>

        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: 16,
            minHeight: 0,
          }}
        >
          {steps.map((step, i) => {
            const p = spring({
              frame,
              fps,
              delay: (0.3 + i * 0.4) * fps,
              config: {damping: 20, mass: 0.7},
            });

            const arrowProgress = interpolate(
              frame,
              [(0.6 + i * 0.4) * fps, (0.95 + i * 0.4) * fps],
              [0, 1],
              {...CLAMP, easing: Easing.out(Easing.cubic)},
            );

            return (
              <React.Fragment key={i}>
                {/* Connecting Clean Arrow */}
                {i > 0 ? (
                  <div
                    style={{
                      flexShrink: 0,
                      width: 50,
                      height: 3,
                      backgroundColor: style.accent,
                      borderRadius: 1.5,
                      transform: `scaleX(${arrowProgress})`,
                      transformOrigin: "left center",
                      opacity: arrowProgress,
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        right: -3,
                        top: -5,
                        width: 0,
                        height: 0,
                        borderTop: "6px solid transparent",
                        borderBottom: "6px solid transparent",
                        borderLeft: `10px solid ${style.accent}`,
                      }}
                    />
                  </div>
                ) : null}

                {/* Step Card */}
                <div
                  style={{
                    ...glassCardStyle,
                    flex: 1,
                    alignSelf: "stretch",
                    padding: 24,
                    display: "flex",
                    flexDirection: "column",
                    gap: 14,
                    opacity: p,
                    transform: `translate3d(0, ${(1 - p) * 40}px, 0)`,
                  }}
                >
                  {scene.images?.[i] ? (
                    <ImageCard
                      src={scene.images[i]}
                      dur={12 * fps}
                      delay={0}
                      kenburns={false}
                      style={{height: 140, flexShrink: 0, borderRadius: 16}}
                    />
                  ) : null}

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div
                      style={{
                        color: style.accent,
                        fontSize: 36,
                        fontWeight: 800,
                        lineHeight: 1,
                      }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <span
                      style={{
                        fontSize: 14,
                        color: style.mutedColor,
                        textTransform: "uppercase",
                        letterSpacing: "0.15em",
                        fontWeight: 600,
                      }}
                    >
                      Step
                    </span>
                  </div>

                  <div style={{fontSize: 28, fontWeight: 700, color: "#ffffff", lineHeight: 1.25}}>
                    {step.title}
                  </div>

                  {step.detail ? (
                    <div
                      style={{
                        fontSize: 20,
                        color: style.mutedColor,
                        lineHeight: 1.4,
                      }}
                    >
                      {step.detail}
                    </div>
                  ) : null}
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </AbsoluteFill>
    </>
  );
};

// ── 5. Stat Scene (Dramatic Count-Up) ───────────────────────────────────────

export const StatScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const value = scene.value ?? 100;

  const count = Math.round(
    interpolate(frame, [fps * 0.5, fps * 2.2], [0, value], {
      ...CLAMP,
      easing: Easing.out(Easing.cubic),
    }),
  );

  const bounce = spring({
    frame,
    fps,
    delay: fps * 2.1,
    config: {damping: 18, mass: 0.65},
  });

  return (
    <>
      <BgImage src={scene.images?.[0]} style={style} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 16,
          textAlign: "center",
        }}
      >
        <AnimatedText
          text={(scene.heading ?? "").toUpperCase()}
          animation="blurIn"
          delay={0.15}
          accent={style.accent}
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: style.accent,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
          }}
        />

        <div
          style={{
            fontSize: 190,
            fontWeight: 900,
            lineHeight: 1,
            letterSpacing: "-0.04em",
            color: "#ffffff",
            textShadow: "0 4px 30px rgba(0,0,0,0.8)",
            transform: `scale(${1 + Math.max(0, bounce - 1) * 0.08})`,
          }}
        >
          {count.toLocaleString("en-IN")}
          <span style={{fontSize: 100, marginLeft: "6px", color: style.accent}}>{scene.suffix ?? ""}</span>
        </div>

        <AnimatedText
          text={scene.label ?? ""}
          animation="slideUp"
          delay={0.9}
          accent={style.accent}
          style={{
            fontSize: 36,
            fontWeight: 600,
            color: "#e2e8f0",
            textAlign: "center",
            maxWidth: 920,
            lineHeight: 1.35,
            textShadow: "0 4px 20px rgba(0,0,0,0.8)",
          }}
        />
      </AbsoluteFill>
    </>
  );
};

// ── 6. Quote Scene ──────────────────────────────────────────────────────────

export const QuoteScene: React.FC<SceneProps> = ({scene, style}) => {
  return (
    <>
      <Background style={style} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: "0 100px",
        }}
      >
        {/* Understated Watermark Quote Mark */}
        <div
          style={{
            position: "absolute",
            top: 40,
            left: 70,
            fontSize: 240,
            color: "rgba(255,255,255,0.04)",
            fontWeight: 900,
            fontFamily: "Georgia, serif",
            lineHeight: 1,
            pointerEvents: "none",
          }}
        >
          &ldquo;
        </div>

        {/* Clean Frosted Quote Card */}
        <div
          style={{
            ...glassCardStyle,
            padding: "50px 70px",
            maxWidth: 1040,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
            boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
          }}
        >
          <AnimatedText
            text={scene.quote ?? ""}
            animation={scene.textAnimation ?? "typewriter"}
            delay={0.3}
            accent={style.accent}
            style={{
              fontSize: 44,
              fontWeight: 600,
              fontStyle: "italic",
              color: "#ffffff",
              textAlign: "center",
              lineHeight: 1.5,
            }}
          />

          {scene.attribution ? (
            <div
              style={{
                marginTop: 36,
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 2,
                  backgroundColor: style.accent,
                }}
              />
              <AnimatedText
                text={scene.attribution}
                animation="slideUp"
                delay={1.8}
                accent={style.accent}
                style={{
                  fontSize: 28,
                  color: style.accent,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              />
              <div
                style={{
                  width: 32,
                  height: 2,
                  backgroundColor: style.accent,
                }}
              />
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </>
  );
};

// ── 7. Outro Scene (High-Converting CTA) ─────────────────────────────────────

export const OutroScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const pulse = 1 + Math.sin(frame / 10) * 0.035;

  const ctaEnter = spring({
    frame,
    fps,
    delay: fps * 1.1,
    config: {damping: 18, mass: 0.65},
  });

  return (
    <>
      <BgImage src={scene.images?.[0]} style={style} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 26,
          textAlign: "center",
          padding: "0 80px",
        }}
      >
        <h1 style={{margin: 0, fontSize: 86, fontWeight: 800, textShadow: "0 10px 40px rgba(0,0,0,0.8)"}}>
          <AnimatedText
            text={scene.title ?? "Thanks for watching!"}
            animation={scene.textAnimation ?? "wordPop"}
            delay={0.25}
            accent={style.accent}
            style={{fontSize: 86, fontWeight: 800, color: style.textColor}}
          />
        </h1>

        {scene.subtitle ? (
          <AnimatedText
            text={scene.subtitle}
            animation="slideUp"
            delay={0.8}
            accent={style.accent}
            style={{
              fontSize: 34,
              color: style.mutedColor,
              fontWeight: 500,
              maxWidth: 800,
              lineHeight: 1.4,
            }}
          />
        ) : null}

        {scene.cta ? (
          <div
            style={{
              marginTop: 26,
              backgroundColor: style.accent,
              color: "#050a14",
              fontSize: 30,
              fontWeight: 800,
              borderRadius: 999,
              padding: "18px 56px",
              transform: `scale(${ctaEnter * pulse})`,
              boxShadow: "0 8px 30px rgba(0,0,0,0.5)",
              letterSpacing: "0.04em",
            }}
          >
            {scene.cta}
          </div>
        ) : null}
      </AbsoluteFill>
    </>
  );
};

// ── 8. Comparison Scene (Before vs After / Old vs New) ─────────────────────

export const ComparisonScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const leftProgress = spring({
    frame,
    fps,
    delay: 0.2 * fps,
    config: {damping: 20, mass: 0.7},
  });

  const rightProgress = spring({
    frame,
    fps,
    delay: 0.5 * fps,
    config: {damping: 20, mass: 0.7},
  });

  const vsEnter = spring({
    frame,
    fps,
    delay: 0.35 * fps,
    config: {damping: 18, mass: 0.6},
  });

  const pulse = 1 + Math.sin(frame / 12) * 0.05;

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "46px 64px", flexDirection: "column"}}>
        <h2 style={{margin: "0 0 24px", textAlign: "center", fontSize: 48, fontWeight: 700}}>
          <AnimatedText
            text={scene.heading ?? "Comparative Analysis"}
            animation={scene.textAnimation ?? "highlight"}
            delay={0.1}
            accent={style.accent}
            style={{fontSize: 48, fontWeight: 700, color: style.accent}}
          />
        </h2>

        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "stretch",
            gap: 28,
            minHeight: 0,
            position: "relative",
          }}
        >
          {/* Left Card: The Friction / Traditional Way */}
          <div
            style={{
              ...glassCardStyle,
              flex: 1,
              padding: 28,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              border: "1px solid rgba(244, 63, 94, 0.25)",
              boxShadow: "0 16px 40px rgba(0,0,0,0.5)",
              opacity: leftProgress,
              transform: `translate3d(${(1 - leftProgress) * -40}px, 0, 0)`,
            }}
          >
            {scene.images?.[0] ? (
              <ImageCard
                src={scene.images[0]}
                dur={10 * fps}
                delay={0}
                kenburns={false}
                style={{height: 160, flexShrink: 0, borderRadius: 16}}
              />
            ) : null}

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                alignSelf: "flex-start",
                padding: "6px 14px",
                borderRadius: 999,
                background: "rgba(244, 63, 94, 0.15)",
                border: "1px solid rgba(244, 63, 94, 0.35)",
                color: "#fda4af",
                fontSize: 16,
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              <span style={{color: "#f43f5e"}}>✕</span>
              {scene.leftLabel ?? "Traditional Way"}
            </div>

            <div style={{display: "flex", flexDirection: "column", gap: 12, marginTop: 4}}>
              {(scene.leftItems ?? ["High friction manual coordination", "Slow disconnected feedback loops", "Error-prone repetitive bottlenecks"]).map((item, idx) => (
                <div key={idx} style={{display: "flex", alignItems: "center", gap: 12, fontSize: 22, color: "#cbd5e1", lineHeight: 1.3}}>
                  <div style={{width: 6, height: 6, borderRadius: "50%", backgroundColor: "#f43f5e", flexShrink: 0}} />
                  {item}
                </div>
              ))}
            </div>
          </div>

          {/* Central Animated VS Badge */}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              transform: `translate(-50%, -50%) scale(${vsEnter * pulse})`,
              zIndex: 30,
              width: 58,
              height: 58,
              borderRadius: "50%",
              background: "#121826",
              border: "1px solid rgba(255,255,255,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: style.accent,
              fontSize: 20,
              fontWeight: 900,
              letterSpacing: "0.08em",
              boxShadow: "0 4px 18px rgba(0,0,0,0.5)",
              opacity: vsEnter,
            }}
          >
            VS
          </div>

          {/* Right Card: The Breakthrough / Modern Way */}
          <div
            style={{
              ...glassCardStyle,
              flex: 1,
              padding: 28,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              border: "1px solid rgba(255,255,255,0.12)",
              boxShadow: "0 16px 40px rgba(0,0,0,0.5)",
              opacity: rightProgress,
              transform: `translate3d(${(1 - rightProgress) * 40}px, 0, 0)`,
            }}
          >
            {scene.images?.[1] ? (
              <ImageCard
                src={scene.images[1]}
                dur={10 * fps}
                delay={0}
                kenburns={false}
                style={{height: 160, flexShrink: 0, borderRadius: 16}}
              />
            ) : null}

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                alignSelf: "flex-start",
                padding: "6px 14px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.14)",
                color: style.accent,
                fontSize: 16,
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
              }}
            >
              <span>✓</span>
              {scene.rightLabel ?? "Modern Breakthrough"}
            </div>

            <div style={{display: "flex", flexDirection: "column", gap: 12, marginTop: 4}}>
              {(scene.rightItems ?? ["Streamlined automated pipeline", "Instant real-time telemetry", "Continuous 10x throughput scaling"]).map((item, idx) => (
                <div key={idx} style={{display: "flex", alignItems: "center", gap: 12, fontSize: 22, color: "#ffffff", fontWeight: 600, lineHeight: 1.3}}>
                  <div style={{width: 6, height: 6, borderRadius: "50%", backgroundColor: style.accent, flexShrink: 0}} />
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </>
  );
};

// ── 9. Bento Grid Scene (Modular Multi-Feature Bento) ───────────────────────

export const BentoScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const heroProgress = spring({
    frame,
    fps,
    delay: 0.15 * fps,
    config: {damping: 20, mass: 0.7},
  });

  const topProgress = spring({
    frame,
    fps,
    delay: 0.45 * fps,
    config: {damping: 20, mass: 0.7},
  });

  const bottomProgress = spring({
    frame,
    fps,
    delay: 0.7 * fps,
    config: {damping: 20, mass: 0.7},
  });

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "44px 64px", flexDirection: "column"}}>
        <h2 style={{margin: "0 0 24px", textAlign: "center", fontSize: 48, fontWeight: 700}}>
          <AnimatedText
            text={scene.heading ?? "Architectural Breakdown"}
            animation={scene.textAnimation ?? "blurIn"}
            delay={0.1}
            accent={style.accent}
            style={{fontSize: 48, fontWeight: 700, color: style.accent}}
          />
        </h2>

        <div
          style={{
            flex: 1,
            display: "flex",
            gap: 24,
            alignItems: "stretch",
            minHeight: 0,
          }}
        >
          {/* Left Column: Big Hero Bento Card (60%) */}
          <div
            style={{
              ...glassCardStyle,
              flex: 1.3,
              padding: 28,
              display: "flex",
              flexDirection: "column",
              gap: 18,
              opacity: heroProgress,
              transform: `translate3d(${(1 - heroProgress) * -35}px, 0, 0)`,
            }}
          >
            {scene.images?.[0] ? (
              <div style={{flex: 1, minHeight: 180, position: "relative"}}>
                <ImageCard
                  src={scene.images[0]}
                  dur={12 * fps}
                  delay={0}
                  style={{width: "100%", height: "100%", borderRadius: 16}}
                />
              </div>
            ) : null}

            <div>
              <div style={{fontSize: 32, fontWeight: 800, color: "#ffffff", lineHeight: 1.2}}>
                {scene.heroTitle ?? scene.title ?? "Core System Architecture"}
              </div>
              <div style={{marginTop: 8, fontSize: 20, color: style.mutedColor, lineHeight: 1.4}}>
                {scene.heroDetail ?? scene.subtitle ?? "Engineered for high-throughput scalability and real-time responsiveness."}
              </div>
            </div>
          </div>

          {/* Right Column: Stacked Bento Mini Cards (40%) */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            {/* Top Stat Mini Card */}
            <div
              style={{
                ...glassCardStyle,
                flex: 1,
                padding: 24,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                opacity: topProgress,
                transform: `translate3d(0, ${(1 - topProgress) * -30}px, 0)`,
              }}
            >
              <div
                style={{
                  fontSize: 68,
                  fontWeight: 900,
                  lineHeight: 1,
                  color: style.accent,
                }}
              >
                {scene.statValue ?? "10x"}
              </div>
              <div style={{marginTop: 8, fontSize: 20, fontWeight: 600, color: style.mutedColor}}>
                {scene.statLabel ?? "Efficiency and throughput acceleration"}
              </div>
            </div>

            {/* Bottom Feature Mini Card */}
            <div
              style={{
                ...glassCardStyle,
                flex: 1,
                padding: 24,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                gap: 8,
                opacity: bottomProgress,
                transform: `translate3d(0, ${(1 - bottomProgress) * 30}px, 0)`,
              }}
            >
              <div style={{fontSize: 26, fontWeight: 700, color: style.accent}}>
                {scene.featureTitle ?? "Synchronized Telemetry"}
              </div>
              <div style={{fontSize: 18, color: "#e2e8f0", lineHeight: 1.35}}>
                {scene.featureDetail ?? "Deep instrumentation tracks every micro-state change automatically."}
              </div>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </>
  );
};

// ── 10. Split Hero Scene (High-Impact 50/50 Concept Showcase) ───────────────

export const SplitHeroScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const textEnter = spring({
    frame,
    fps,
    delay: 0.15 * fps,
    config: {damping: 20, mass: 0.7},
  });

  const cardEnter = spring({
    frame,
    fps,
    delay: 0.35 * fps,
    config: {damping: 20, mass: 0.7},
  });

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "50px 70px", flexDirection: "row", alignItems: "center", gap: 50}}>
        {/* Left Side: Typography & Bullets */}
        <div
          style={{
            flex: 1.1,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            opacity: textEnter,
            transform: `translate3d(${(1 - textEnter) * -40}px, 0, 0)`,
          }}
        >
          {scene.badge ? (
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                alignSelf: "flex-start",
                padding: "8px 18px",
                borderRadius: 999,
                background: "rgba(18, 24, 38, 0.85)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: style.accent,
                fontSize: 16,
                fontWeight: 700,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}
            >
              <span style={{width: 6, height: 6, borderRadius: "50%", backgroundColor: style.accent}} />
              {scene.badge}
            </div>
          ) : null}

          <h2 style={{margin: 0, fontSize: 56, fontWeight: 800, lineHeight: 1.15, letterSpacing: "-0.02em"}}>
            <AnimatedText
              text={scene.title ?? scene.heading ?? ""}
              animation={scene.textAnimation ?? "wordPop"}
              delay={0.2}
              accent={style.accent}
              style={{fontSize: 56, fontWeight: 800, color: style.textColor}}
            />
          </h2>

          {scene.subtitle ? (
            <p style={{margin: 0, fontSize: 24, color: style.mutedColor, lineHeight: 1.4}}>
              {scene.subtitle}
            </p>
          ) : null}

          {scene.bullets?.length ? (
            <div style={{display: "flex", flexDirection: "column", gap: 12, marginTop: 8}}>
              {scene.bullets.slice(0, 3).map((b, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    fontSize: 22,
                    fontWeight: 600,
                    color: "#f1f5f9",
                  }}
                >
                  <div style={{width: 8, height: 8, borderRadius: "50%", backgroundColor: style.accent, flexShrink: 0}} />
                  {b}
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {/* Right Side: Large 3D Image Card */}
        {scene.images?.[0] ? (
          <div
            style={{
              flex: 0.9,
              height: "100%",
              maxHeight: 480,
              opacity: cardEnter,
              transform: `translate3d(${(1 - cardEnter) * 40}px, 0, 0)`,
            }}
          >
            <ImageCard
              src={scene.images[0]}
              dur={12 * fps}
              delay={0}
              style={{width: "100%", height: "100%", borderRadius: 24}}
            />
          </div>
        ) : null}
      </AbsoluteFill>
    </>
  );
};
