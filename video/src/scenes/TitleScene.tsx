import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";
import { BrandLogo } from "../components/BrandLogo";

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title text animation
  const titleY = interpolate(frame, [15, 40], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtitle
  const subOpacity = interpolate(frame, [35, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subY = interpolate(frame, [35, 55], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Decorative line
  const lineWidth = spring({
    frame: frame - 50,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.midnightBlue,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Logo */}
      <BrandLogo size={100} delay={0} />

      {/* Title */}
      <div
        style={{
          marginTop: 40,
          transform: `translateY(${titleY}px)`,
          opacity: titleOpacity,
        }}
      >
        <h1
          style={{
            fontFamily: FONT.family,
            fontSize: 56,
            fontWeight: "bold",
            color: COLORS.white,
            textAlign: "center",
            margin: 0,
          }}
        >
          AI Recommendation Engine
        </h1>
      </div>

      {/* Decorative line */}
      <div
        style={{
          marginTop: 24,
          width: lineWidth * 200,
          height: 3,
          background: COLORS.rose,
        }}
      />

      {/* Subtitle */}
      <div
        style={{
          marginTop: 20,
          transform: `translateY(${subY}px)`,
          opacity: subOpacity,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.subheading.size,
            color: COLORS.turquoise,
            textAlign: "center",
            margin: 0,
          }}
        >
          How RMG scores and recommends the best resource
        </p>
      </div>

      {/* Bottom brand text */}
      <div
        style={{
          position: "absolute",
          bottom: 50,
          opacity: subOpacity,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            color: COLORS.white,
            opacity: 0.5,
            margin: 0,
          }}
        >
          Jman Group &middot; RMG Engine
        </p>
      </div>
    </AbsoluteFill>
  );
};
