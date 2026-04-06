import React from 'react';
import Svg, {
  Circle,
  Rect,
  Path,
  G,
  Ellipse,
  Line,
  Polygon,
  Text as SvgText,
} from 'react-native-svg';

// ─────────────────────────────────────────
// BALLOON ARCH  (default 120 × 110)
// ─────────────────────────────────────────
export function BalloonArch({ color = '#C084FC', width = 120, height = 110 }) {
  const scaleX = width / 120;
  const scaleY = height / 110;

  // Arch positions  [cx, cy, r]  on a 120×110 grid
  const balloons = [
    [10, 100, 11],
    [26, 76, 11],
    [42, 54, 11],
    [60, 38, 12],
    [78, 54, 11],
    [94, 76, 11],
    [110, 100, 11],
  ];

  const secondRow = [
    [18, 87, 9],
    [34, 65, 9],
    [52, 46, 9],
    [68, 46, 9],
    [86, 65, 9],
    [102, 87, 9],
  ];

  // Darker shade for depth
  const darken = (hex) => {
    const n = parseInt(hex.replace('#', ''), 16);
    const r = Math.max(0, ((n >> 16) & 0xff) - 40);
    const g = Math.max(0, ((n >> 8) & 0xff) - 40);
    const b = Math.max(0, (n & 0xff) - 40);
    return `rgb(${r},${g},${b})`;
  };

  return (
    <Svg width={width} height={height} viewBox="0 0 120 110">
      {/* String connecting balloons */}
      <Path
        d="M10 100 Q35 60 60 38 Q85 60 110 100"
        stroke="rgba(0,0,0,0.25)"
        strokeWidth="1"
        fill="none"
      />
      {/* Back row (slightly darker) */}
      {secondRow.map(([cx, cy, r], i) => (
        <Circle key={`b${i}`} cx={cx} cy={cy} r={r} fill={darken(color)} opacity={0.75} />
      ))}
      {/* Front row */}
      {balloons.map(([cx, cy, r], i) => (
        <G key={`f${i}`}>
          <Circle cx={cx} cy={cy} r={r} fill={color} />
          {/* Shine */}
          <Circle cx={cx - r * 0.3} cy={cy - r * 0.3} r={r * 0.2} fill="rgba(255,255,255,0.45)" />
          {/* Knot */}
          <Circle cx={cx} cy={cy + r} r={1.5} fill={darken(color)} />
          {/* String to base */}
          <Line
            x1={cx}
            y1={cy + r + 1}
            x2={cx}
            y2={cy + r + 6}
            stroke="rgba(0,0,0,0.3)"
            strokeWidth="0.8"
          />
        </G>
      ))}
    </Svg>
  );
}

// ─────────────────────────────────────────
// ROUND TABLE  (default 100 × 90)
// ─────────────────────────────────────────
export function TableRound({ color = '#60A5FA', width = 100, height = 90 }) {
  return (
    <Svg width={width} height={height} viewBox="0 0 100 90">
      {/* Tablecloth drape shadow */}
      <Ellipse cx={50} cy={56} rx={44} ry={12} fill="rgba(0,0,0,0.15)" />
      {/* Tablecloth */}
      <Ellipse cx={50} cy={50} rx={44} ry={14} fill={color} />
      {/* Table top surface */}
      <Ellipse cx={50} cy={44} rx={40} ry={12} fill={color} opacity={0.9} />
      {/* Highlight */}
      <Ellipse cx={42} cy={40} rx={16} ry={5} fill="rgba(255,255,255,0.3)" />
      {/* Table edge ring */}
      <Ellipse cx={50} cy={44} rx={40} ry={12} fill="none" stroke="rgba(0,0,0,0.15)" strokeWidth="1" />
    </Svg>
  );
}

// ─────────────────────────────────────────
// BACKDROP  (default 100 × 150)
// ─────────────────────────────────────────
export function Backdrop({ color = '#F472B6', width = 100, height = 150 }) {
  return (
    <Svg width={width} height={height} viewBox="0 0 100 150">
      {/* Frame post left */}
      <Rect x={4} y={0} width={5} height={150} rx={2} fill="rgba(0,0,0,0.3)" />
      {/* Frame post right */}
      <Rect x={91} y={0} width={5} height={150} rx={2} fill="rgba(0,0,0,0.3)" />
      {/* Top bar */}
      <Rect x={2} y={0} width={96} height={6} rx={3} fill="rgba(0,0,0,0.35)" />
      {/* Fabric panel */}
      <Rect x={9} y={6} width={82} height={144} rx={2} fill={color} />
      {/* Fabric sheen */}
      <Rect x={14} y={10} width={20} height={135} rx={2} fill="rgba(255,255,255,0.15)" />
      {/* Fabric fold lines */}
      <Line x1={35} y1={6} x2={35} y2={150} stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
      <Line x1={55} y1={6} x2={55} y2={150} stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
      <Line x1={75} y1={6} x2={75} y2={150} stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
      {/* Bottom fringe */}
      {Array.from({ length: 14 }).map((_, i) => (
        <Line
          key={i}
          x1={12 + i * 6}
          y1={150}
          x2={12 + i * 6}
          y2={155}
          stroke={color}
          strokeWidth="2"
          opacity={0.8}
        />
      ))}
    </Svg>
  );
}

// ─────────────────────────────────────────
// THRONE  (default 90 × 130)
// ─────────────────────────────────────────
export function Throne({ color = '#FBBF24', width = 90, height = 130 }) {
  return (
    <Svg width={width} height={height} viewBox="0 0 90 130">
      {/* Back legs */}
      <Rect x={12} y={90} width={8} height={38} rx={3} fill="rgba(0,0,0,0.35)" />
      <Rect x={70} y={90} width={8} height={38} rx={3} fill="rgba(0,0,0,0.35)" />
      {/* Front legs */}
      <Rect x={18} y={92} width={8} height={36} rx={3} fill="rgba(0,0,0,0.25)" />
      <Rect x={64} y={92} width={8} height={36} rx={3} fill="rgba(0,0,0,0.25)" />
      {/* Seat */}
      <Rect x={10} y={78} width={70} height={16} rx={5} fill={color} />
      {/* Seat cushion */}
      <Rect x={14} y={80} width={62} height={10} rx={4} fill="rgba(255,255,255,0.25)" />
      {/* Armrests */}
      <Rect x={5} y={60} width={12} height={28} rx={4} fill={color} />
      <Rect x={73} y={60} width={12} height={28} rx={4} fill={color} />
      {/* Chair back */}
      <Rect x={10} y={8} width={70} height={74} rx={8} fill={color} />
      {/* Back cushion highlight */}
      <Rect x={16} y={14} width={58} height={60} rx={6} fill="rgba(255,255,255,0.18)" />
      {/* Crown decoration on top */}
      <Polygon
        points="45,2 40,12 30,8 35,18 25,16 32,26 58,26 65,16 55,18 60,8 50,12"
        fill={color}
        stroke="rgba(0,0,0,0.2)"
        strokeWidth="1"
      />
      {/* Crown gems */}
      <Circle cx={45} cy={6} r={3} fill="rgba(255,255,255,0.6)" />
      <Circle cx={35} cy={12} r={2} fill="rgba(255,255,255,0.4)" />
      <Circle cx={55} cy={12} r={2} fill="rgba(255,255,255,0.4)" />
    </Svg>
  );
}

// ─────────────────────────────────────────
// MARQUEE FRAME  (default 140 × 80)
// ─────────────────────────────────────────
export function Marquee({ color = '#34D399', width = 140, height = 80 }) {
  return (
    <Svg width={width} height={height} viewBox="0 0 140 80">
      {/* Outer frame */}
      <Rect x={2} y={2} width={136} height={76} rx={6} fill="none" stroke={color} strokeWidth={4} />
      {/* Inner frame */}
      <Rect x={10} y={10} width={120} height={60} rx={4} fill="rgba(0,0,0,0.05)" stroke={color} strokeWidth={2} strokeDasharray="6,3" />
      {/* Corner stars */}
      {[[14, 14], [126, 14], [14, 66], [126, 66]].map(([cx, cy], i) => (
        <Circle key={i} cx={cx} cy={cy} r={4} fill={color} opacity={0.8} />
      ))}
      {/* Bulb lights */}
      {Array.from({ length: 10 }).map((_, i) => (
        <Circle
          key={`t${i}`}
          cx={20 + i * 12}
          cy={6}
          r={3.5}
          fill={i % 2 === 0 ? color : 'rgba(255,255,255,0.8)'}
          opacity={0.9}
        />
      ))}
      {Array.from({ length: 10 }).map((_, i) => (
        <Circle
          key={`b${i}`}
          cx={20 + i * 12}
          cy={74}
          r={3.5}
          fill={i % 2 === 0 ? color : 'rgba(255,255,255,0.8)'}
          opacity={0.9}
        />
      ))}
      {/* Side lights */}
      {Array.from({ length: 5 }).map((_, i) => (
        <Circle key={`l${i}`} cx={6} cy={16 + i * 12} r={3} fill={color} opacity={0.7} />
      ))}
      {Array.from({ length: 5 }).map((_, i) => (
        <Circle key={`r${i}`} cx={134} cy={16 + i * 12} r={3} fill={color} opacity={0.7} />
      ))}
      {/* Label area */}
      <SvgText
        x={70}
        y={44}
        fontSize={11}
        fontWeight="bold"
        fill={color}
        textAnchor="middle"
        letterSpacing={2}
      >
        MARQUEE
      </SvgText>
    </Svg>
  );
}

// ─────────────────────────────────────────
// CATALOG for the palette
// ─────────────────────────────────────────
export const DECORATION_CATALOG = [
  {
    type: 'balloon_arch',
    label: 'Balloon Arch',
    emoji: '🎈',
    defaultColor: '#C084FC',
    defaultWidth: 120,
    defaultHeight: 110,
    Component: BalloonArch,
  },
  {
    type: 'table',
    label: 'Round Table',
    emoji: '🪑',
    defaultColor: '#60A5FA',
    defaultWidth: 100,
    defaultHeight: 90,
    Component: TableRound,
  },
  {
    type: 'backdrop',
    label: 'Backdrop',
    emoji: '🖼️',
    defaultColor: '#F472B6',
    defaultWidth: 100,
    defaultHeight: 150,
    Component: Backdrop,
  },
  {
    type: 'throne',
    label: 'Throne',
    emoji: '👑',
    defaultColor: '#FBBF24',
    defaultWidth: 90,
    defaultHeight: 130,
    Component: Throne,
  },
  {
    type: 'marquee',
    label: 'Marquee',
    emoji: '✨',
    defaultColor: '#34D399',
    defaultWidth: 140,
    defaultHeight: 80,
    Component: Marquee,
  },
];

export function getComponentByType(type) {
  return DECORATION_CATALOG.find((d) => d.type === type)?.Component;
}
