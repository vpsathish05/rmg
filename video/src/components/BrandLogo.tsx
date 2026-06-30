import React from "react";
import { interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS } from "../styles/brand";

export const BrandLogo: React.FC<{
  size?: number;
  delay?: number;
}> = ({ size = 80, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  const opacity = interpolate(frame - delay, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: size,
        height: size,
        transform: `scale(${scale})`,
        opacity,
      }}
    >
      <svg viewBox="0 0 32 32" width={size} height={size}>
        <rect width="32" height="32" rx="0" fill={COLORS.midnightBlue} />
        <text
          x="16"
          y="23"
          textAnchor="middle"
          fontFamily="Arial, sans-serif"
          fontWeight="900"
          fontSize="20"
          fill={COLORS.white}
        >
          J
        </text>
      </svg>
    </div>
  );
};
