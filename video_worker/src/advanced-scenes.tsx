import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {AnimatedText} from "./AnimatedText";
import {Background} from "./scenes";
import type {SceneProps} from "./scenes";

const CLAMP = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;

const panelStyle: React.CSSProperties = {
  background: "rgba(18, 24, 38, 0.72)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 22,
  boxShadow: "0 16px 40px rgba(0,0,0,0.5)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
};

const SceneHeading: React.FC<{
  text: string;
  accent: string;
  animation?: SceneProps["scene"]["textAnimation"];
}> = ({text, accent, animation = "blurIn"}) => (
  <h2
    style={{
      margin: 0,
      textAlign: "center",
      fontSize: 48,
      fontWeight: 750,
      letterSpacing: "-0.02em",
    }}
  >
    <AnimatedText
      text={text}
      animation={animation}
      delay={0.1}
      accent={accent}
      style={{fontSize: 48, fontWeight: 750, color: accent}}
    />
  </h2>
);

/** Evidence-led horizontal bar chart for topics with comparable measurements. */
export const ChartScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const points = scene.data?.slice(0, 5) ?? [];
  const maxValue = Math.max(1, ...points.map((point) => point.value));

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "48px 72px", flexDirection: "column"}}>
        <SceneHeading
          text={scene.heading ?? "Measured Impact"}
          accent={style.accent}
          animation={scene.textAnimation ?? "gradientWave"}
        />

        <div
          style={{
            ...panelStyle,
            flex: 1,
            marginTop: 30,
            padding: "30px 38px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: 18,
          }}
        >
          {points.map((point, index) => {
            const progress = spring({
              frame,
              fps,
              delay: (0.25 + index * 0.16) * fps,
              config: {damping: 22, mass: 0.65, stiffness: 120},
            });
            const width = `${(point.value / maxValue) * 100 * progress}%`;

            return (
              <div
                key={`${point.label}-${index}`}
                style={{display: "flex", alignItems: "center", gap: 18, minHeight: 66}}
              >
                <div
                  style={{
                    width: 190,
                    flexShrink: 0,
                    color: "#e8eef8",
                    fontSize: 22,
                    fontWeight: 650,
                    lineHeight: 1.15,
                  }}
                >
                  <div>{point.label}</div>
                  {point.detail ? (
                    <div style={{marginTop: 5, color: "#8291a8", fontSize: 14, fontWeight: 500}}>
                      {point.detail}
                    </div>
                  ) : null}
                </div>
                <div
                  style={{
                    flex: 1,
                    height: 30,
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.08)",
                    overflow: "hidden",
                    boxShadow: "inset 0 1px 4px rgba(0,0,0,0.35)",
                  }}
                >
                  <div
                    style={{
                      width,
                      height: "100%",
                      borderRadius: 999,
                      backgroundColor: style.accent,
                    }}
                  />
                </div>
                <div
                  style={{
                    width: 100,
                    flexShrink: 0,
                    color: "#ffffff",
                    fontSize: 30,
                    fontWeight: 850,
                    textAlign: "right",
                  }}
                >
                  {Math.round(point.value * progress)}
                  {scene.suffix ?? ""}
                </div>
              </div>
            );
          })}
          {!points.length ? (
            <div style={{color: style.mutedColor, fontSize: 26, textAlign: "center"}}>
              Add three to five measured data points to render this chart.
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </>
  );
};

/** Chronological milestone rail for history, evolution, or phased progress. */
export const TimelineScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const events = scene.timeline?.slice(0, 4) ?? [];
  const railProgress = interpolate(frame, [0, 1.5 * fps], [0, 1], {
    ...CLAMP,
    easing: Easing.out(Easing.cubic),
  });

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "48px 64px", flexDirection: "column"}}>
        <SceneHeading
          text={scene.heading ?? "The Evolution"}
          accent={style.accent}
          animation={scene.textAnimation ?? "letterDrop"}
        />

        <div
          style={{
            flex: 1,
            marginTop: 34,
            position: "relative",
            display: "flex",
            alignItems: "center",
            gap: 18,
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 45,
              right: 45,
              top: "calc(50% + 135px)",
              height: 4,
              borderRadius: 4,
              background: "rgba(255,255,255,0.1)",
            }}
          >
            <div
              style={{
                width: `${railProgress * 100}%`,
                height: "100%",
                borderRadius: 4,
                backgroundColor: style.accent,
              }}
            />
          </div>

          {events.map((event, index) => {
            const enter = spring({
              frame,
              fps,
              delay: (0.25 + index * 0.22) * fps,
              config: {damping: 20, mass: 0.7, stiffness: 115},
            });

            return (
              <div
                key={`${event.label}-${index}`}
                style={{
                  ...panelStyle,
                  flex: 1,
                  minWidth: 0,
                  minHeight: 270,
                  padding: 22,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  position: "relative",
                  opacity: enter,
                  transform: `translate3d(0, ${(1 - enter) * 35}px, 0)`,
                  zIndex: 1,
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: "100%",
                    left: "50%",
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    backgroundColor: style.accent,
                    border: "4px solid #081223",
                    transform: "translate(-50%, -50%)",
                  }}
                />
                <div
                  style={{
                    color: style.accent,
                    fontSize: 18,
                    fontWeight: 800,
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                  }}
                >
                  {event.label}
                </div>
                <div style={{marginTop: 14, color: "#ffffff", fontSize: 27, fontWeight: 750, lineHeight: 1.2}}>
                  {event.title}
                </div>
                {event.detail ? (
                  <div style={{marginTop: 10, color: style.mutedColor, fontSize: 19, lineHeight: 1.4}}>
                    {event.detail}
                  </div>
                ) : null}
              </div>
            );
          })}
          {!events.length ? (
            <div style={{width: "100%", color: style.mutedColor, fontSize: 26, textAlign: "center"}}>
              Add three or four milestones to render this timeline.
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </>
  );
};

/** Action-oriented checklist with progressive completion and a compact summary badge. */
export const ChecklistScene: React.FC<SceneProps> = ({scene, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items = scene.items?.slice(0, 5) ?? [];
  const completion = interpolate(frame, [0.35 * fps, 2.3 * fps], [0, 1], {
    ...CLAMP,
    easing: Easing.out(Easing.cubic),
  });
  const completedCount = Math.round(items.length * completion);
  const circumference = 2 * Math.PI * 44;

  return (
    <>
      <Background style={style} />
      <AbsoluteFill style={{padding: "48px 72px", flexDirection: "column"}}>
        <SceneHeading
          text={scene.heading ?? "Execution Checklist"}
          accent={style.accent}
          animation={scene.textAnimation ?? "highlight"}
        />

        <div style={{flex: 1, display: "flex", gap: 38, alignItems: "center", marginTop: 24}}>
          <div
            style={{
              ...panelStyle,
              width: 220,
              height: 220,
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
            }}
          >
            <svg width="150" height="150" viewBox="0 0 120 120" style={{transform: "rotate(-90deg)"}}>
              <circle cx="60" cy="60" r="44" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="10" />
              <circle
                cx="60"
                cy="60"
                r="44"
                fill="none"
                stroke={style.accent}
                strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference * (1 - completion)}
              />
            </svg>
            <div style={{position: "absolute", textAlign: "center"}}>
              <div style={{fontSize: 44, fontWeight: 850, color: "#ffffff"}}>{completedCount}</div>
              <div style={{fontSize: 16, color: style.mutedColor, letterSpacing: "0.12em", textTransform: "uppercase"}}>
                of {items.length || 3} ready
              </div>
            </div>
          </div>

          <div style={{flex: 1, display: "flex", flexDirection: "column", gap: 16}}>
            {items.map((item, index) => {
              const enter = spring({
                frame,
                fps,
                delay: (0.3 + index * 0.28) * fps,
                config: {damping: 21, mass: 0.7},
              });
              const checked = interpolate(
                frame,
                [(0.7 + index * 0.28) * fps, (1.05 + index * 0.28) * fps],
                [0, 1],
                CLAMP,
              );

              return (
                <div
                  key={`${item.title}-${index}`}
                  style={{
                    ...panelStyle,
                    padding: "16px 22px",
                    display: "flex",
                    alignItems: "center",
                    gap: 18,
                    opacity: enter,
                    transform: `translate3d(${(1 - enter) * 40}px, 0, 0)`,
                  }}
                >
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      flexShrink: 0,
                      borderRadius: 12,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#03101d",
                      fontSize: 24,
                      fontWeight: 900,
                      backgroundColor: style.accent,
                      opacity: 0.35 + checked * 0.65,
                    }}
                  >
                    ✓
                  </div>
                  <div style={{minWidth: 0}}>
                    <div style={{color: "#ffffff", fontSize: 25, fontWeight: 750}}>{item.title}</div>
                    {item.detail ? (
                      <div style={{marginTop: 4, color: style.mutedColor, fontSize: 18, lineHeight: 1.35}}>{item.detail}</div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </>
  );
};
