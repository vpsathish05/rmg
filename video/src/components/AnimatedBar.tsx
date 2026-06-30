import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";

export const AnimatedBar: React.FC<{
  label: string;
  value: number; // 0-1
  weight: string; // e.g. "0.40"
  color: string;
  delay?: number;
  y?: number;
  barWidth?: number;
}> = ({ label, value, weight, color, delay = 0, y = 0, barWidth = 600 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame - delay, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const fillWidth = spring({
    frame: frame - delay - 10,
    fps,
    config: { damping: 20, stiffness: 80 },
  });

  const currentWidth = fillWidth * value * barWidth;

  return (
    <div
      style={{
        position: "absolute",
        left: 200,
        top: y,
        opacity,
        display: "flex",
        alignItems: "center",
        gap: 20,
      }}
    >
      {/* Label */}
      <div
        style={{
          width: 200,
          textAlign: "right",
          fontFamily: FONT.family,
          fontSize: FONT.body.size,
          fontWeight: "bold",
          color: COLORS.midnightBlue,
        }}
      >
        {label}
      </div>

      {/* Bar background */}
      <div
        style={{
          width: barWidth,
          height: 40,
          background: COLORS.greyLight,
          border: `1px solid ${COLORS.grey}`,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Fill */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: currentWidth,
            background: color,
          }}
        />
      </div>

      {/* Weight label */}
      <div
        style={{
          fontFamily: FONT.family,
          fontSize: FONT.body.size,
          color: COLORS.midnightBlue,
          fontWeight: "bold",
          minWidth: 80,
        }}
      >
        x{weight}
      </div>
    </div>
  );
};
