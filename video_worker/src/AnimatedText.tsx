import React from "react";
import {
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type {CSSProperties} from "react";
import type {TextAnimation} from "./types";

const CLAMP = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;

/**
 * Kinetic text renderer — enhanced with fluid physics, glowing typography,
 * and high-end motion design for professional video presentation.
 */
export const AnimatedText: React.FC<{
  text: string;
  animation?: TextAnimation;
  delay?: number; // seconds before the animation starts
  accent?: string;
  style?: CSSProperties;
}> = ({text, animation = "slideUp", delay = 0, accent = "#3ec1f0", style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const d = delay * fps; // delay in frames

  switch (animation) {
    case "wordPop":
      return (
        <span style={{...style}}>
          {text.split(" ").map((w, i) => {
            const p = spring({
              frame,
              fps,
              delay: d + i * 0.08 * fps,
              config: {damping: 18, mass: 0.65, stiffness: 130},
            });
            const opacity = interpolate(p, [0, 0.4, 1], [0, 0.8, 1]);
            const translateY = (1 - p) * 28;
            const scale = 0.7 + p * 0.3;
            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  opacity,
                  transform: `translate3d(0, ${translateY}px, 0) scale(${scale})`,
                  marginRight: "0.28em",
                  willChange: "transform, opacity",
                }}
              >
                {w}
              </span>
            );
          })}
        </span>
      );

    case "glowReveal": {
      const words = text.split(" ");
      return (
        <span style={{...style}}>
          {words.map((w, i) => {
            const p = spring({
              frame,
              fps,
              delay: d + i * 0.07 * fps,
              config: {damping: 18, mass: 0.65, stiffness: 120},
            });
            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  opacity: p,
                  transform: `translate3d(0, ${(1 - p) * 16}px, 0) scale(${0.9 + p * 0.1})`,
                  marginRight: "0.28em",
                }}
              >
                {w}
              </span>
            );
          })}
        </span>
      );
    }

    case "gradientWave": {
      const p = interpolate(frame, [d, d + fps * 0.55], [0, 1], {
        ...CLAMP,
        easing: Easing.out(Easing.cubic),
      });
      return (
        <span
          style={{
            ...style,
            display: "inline-block",
            opacity: p,
            transform: `translate3d(0, ${(1 - p) * 18}px, 0)`,
            letterSpacing: `${(1 - p) * 0.05}em`,
          }}
        >
          {text}
        </span>
      );
    }

    case "typewriter": {
      const len = text.length;
      const chars = Math.floor(
        interpolate(frame, [d, d + Math.max(10, len * 1.5)], [0, len], CLAMP),
      );
      const cursorBlink = Math.floor(frame / (fps / 3)) % 2 === 0;
      return (
        <span style={{...style}}>
          {text.slice(0, chars)}
          <span
            style={{
              color: accent,
              opacity: chars < len ? 1 : cursorBlink ? 1 : 0,
              fontWeight: 400,
              marginLeft: "3px",
            }}
          >
            |
          </span>
        </span>
      );
    }

    case "letterDrop":
      return (
        <span style={{...style}}>
          {text.split("").map((ch, i) => {
            const p = spring({
              frame,
              fps,
              delay: d + i * 0.025 * fps,
              config: {damping: 18, mass: 0.65, stiffness: 130},
            });
            return (
              <span
                key={i}
                style={{
                  display: "inline-block",
                  opacity: Math.min(1, p * 1.8),
                  transform: `translate3d(0, ${-40 * (1 - p)}px, 0)`,
                }}
              >
                {ch === " " ? "\u00A0" : ch}
              </span>
            );
          })}
        </span>
      );

    case "highlight": {
      const pct = interpolate(frame, [d + fps * 0.2, d + fps * 0.8], [0, 1], {
        ...CLAMP,
        easing: Easing.out(Easing.quad),
      });
      const enter = interpolate(frame, [d, d + fps * 0.45], [0, 1], {
        ...CLAMP,
        easing: Easing.out(Easing.cubic),
      });
      return (
        <span
          style={{
            ...style,
            display: "inline-block",
            opacity: enter,
            transform: `translate3d(${-24 * (1 - enter)}px, 0, 0)`,
            backgroundImage: `linear-gradient(${accent}55, ${accent}55)`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "0% 86%",
            backgroundSize: `${pct * 100}% 36%`,
            padding: "0 0.12em",
            borderRadius: "4px",
          }}
        >
          {text}
        </span>
      );
    }

    case "blurIn": {
      const p = interpolate(frame, [d, d + fps * 0.75], [0, 1], {
        ...CLAMP,
        easing: Easing.out(Easing.cubic),
      });
      return (
        <span
          style={{
            ...style,
            display: "inline-block",
            opacity: p,
            filter: `blur(${(1 - p) * 12}px)`,
            letterSpacing: `${(1 - p) * 0.08}em`,
            transform: `translate3d(0, ${(1 - p) * 15}px, 0)`,
          }}
        >
          {text}
        </span>
      );
    }

    case "slideUp":
    default: {
      const p = interpolate(frame, [d, d + fps * 0.55], [0, 1], {
        ...CLAMP,
        easing: Easing.out(Easing.cubic),
      });
      return (
        <span
          style={{
            ...style,
            display: "inline-block",
            opacity: p,
            transform: `translate3d(0, ${36 * (1 - p)}px, 0)`,
          }}
        >
          {text}
        </span>
      );
    }
  }
};
