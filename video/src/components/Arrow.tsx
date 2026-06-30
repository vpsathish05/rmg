import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../styles/brand";

export const Arrow: React.FC<{
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  delay?: number;
  color?: string;
  dashed?: boolean;
}> = ({ x1, y1, x2, y2, delay = 0, color = COLORS.midnightBlue, dashed = false }) => {
  const frame = useCurrentFrame();

  const progress = interpolate(frame - delay, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);

  // Arrow head size (isosceles, height = 1/8 of base as per brand)
  const headLength = 12;
  const headWidth = 8;

  // Line end point (stop before arrowhead)
  const lineEndX = x1 + (dx * (length - headLength)) / length;
  const lineEndY = y1 + (dy * (length - headLength)) / length;

  const dashOffset = (1 - progress) * length;

  return (
    <svg
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        overflow: "visible",
      }}
    >
      {/* Line */}
      <line
        x1={x1}
        y1={y1}
        x2={lineEndX}
        y2={lineEndY}
        stroke={color}
        strokeWidth={2}
        strokeDasharray={dashed ? "8 4" : `${length}`}
        strokeDashoffset={dashed ? 0 : dashOffset}
      />
      {/* Arrow head (isosceles triangle) */}
      {progress > 0.8 && (
        <polygon
          points={`
            ${x2},${y2}
            ${x2 - headLength * Math.cos(angle) + headWidth * Math.sin(angle)},${y2 - headLength * Math.sin(angle) - headWidth * Math.cos(angle)}
            ${x2 - headLength * Math.cos(angle) - headWidth * Math.sin(angle)},${y2 - headLength * Math.sin(angle) + headWidth * Math.cos(angle)}
          `}
          fill={color}
          opacity={interpolate(progress, [0.8, 1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })}
        />
      )}
    </svg>
  );
};
