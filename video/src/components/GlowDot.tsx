import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export const GlowDot: React.FC<{
  x: number;
  y: number;
  color: string;
  size?: number;
  delay?: number;
  pulse?: boolean;
}> = ({ x, y, color, size = 10, delay = 0, pulse = false }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame - delay, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const pulseScale = pulse
    ? 1 + 0.2 * Math.sin((frame - delay) * 0.15)
    : 1;

  return (
    <div
      style={{
        position: "absolute",
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        opacity,
        transform: `scale(${pulseScale})`,
        boxShadow: `0 0 ${size}px ${color}`,
      }}
    />
  );
};
