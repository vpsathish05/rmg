import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";

type NodeVariant = "primary" | "secondary" | "accent" | "highlight";

const VARIANT_STYLES: Record<NodeVariant, { bg: string; text: string; border: string }> = {
  primary: { bg: COLORS.trypanBlue, text: COLORS.white, border: COLORS.midnightBlue },
  secondary: { bg: COLORS.greyLight, text: COLORS.midnightBlue, border: COLORS.grey },
  accent: { bg: COLORS.turquoise, text: COLORS.midnightBlue, border: COLORS.emerald },
  highlight: { bg: COLORS.rose, text: COLORS.white, border: COLORS.berry },
};

export const FlowNode: React.FC<{
  label: string;
  variant?: NodeVariant;
  delay?: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  active?: boolean;
  subtitle?: string;
}> = ({ label, variant = "primary", delay = 0, x = 0, y = 0, width = 240, height = 70, active = true, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 14, stiffness: 120 },
  });

  const opacity = interpolate(frame - delay, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const style = VARIANT_STYLES[variant];

  // Glow effect when active
  const glowOpacity = active
    ? interpolate(frame - delay, [15, 25], [0, 0.4], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height,
        transform: `scale(${scale})`,
        opacity,
      }}
    >
      {/* Glow */}
      {active && (
        <div
          style={{
            position: "absolute",
            inset: -4,
            background: style.bg,
            opacity: glowOpacity,
            filter: "blur(12px)",
          }}
        />
      )}
      {/* Node */}
      <div
        style={{
          width: "100%",
          height: "100%",
          background: style.bg,
          border: `2px solid ${style.border}`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        <span
          style={{
            color: style.text,
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            fontWeight: "bold",
          }}
        >
          {label}
        </span>
        {subtitle && (
          <span
            style={{
              color: style.text,
              fontFamily: FONT.family,
              fontSize: FONT.small.size,
              opacity: 0.8,
              marginTop: 2,
            }}
          >
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
};
