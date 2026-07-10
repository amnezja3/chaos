"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Signal = {
  id: string;
  channel: string;
  title: string;
  label: string;
  value: string;
  stat: string;
  timer: string;
  cta: string;
  tone: "lime" | "amber" | "cyan" | "red";
  layout: 1 | 2 | 3 | 4 | 5 | 6;
  radarSides: 0 | 4 | 5 | 6 | 7 | 8;
  nodes: Array<[number, number, number]>;
};

const signals: Signal[] = [
  {
    id: "hotspot-mokotow",
    channel: "PRZECHWYCONY KANAŁ",
    title: "HOTSPOT / MOKOTÓW",
    label: "WZROST RUCHU",
    value: "240%",
    stat: "17 AKTYWNYCH OPERACJI",
    timer: "04:32",
    cta: "PRZECHWYĆ TELEPORT",
    tone: "lime",
    layout: 1,
    radarSides: 0,
    nodes: [[22, 26, 3], [34, 43, 2], [66, 27, 3], [78, 51, 4], [63, 72, 3], [31, 69, 2]],
  },
  {
    id: "market-gps",
    channel: "GHOST MARKET WATCH",
    title: "GPS LOGS / WARSZAWA",
    label: "POTENCJAŁ CENY",
    value: "+34%",
    stat: "62 PAKIETY W RUCHU",
    timer: "08:18",
    cta: "OTWÓRZ GHOST EXCHANGE",
    tone: "cyan",
    layout: 2,
    radarSides: 4,
    nodes: [[19, 57, 2], [31, 31, 4], [46, 62, 2], [61, 38, 3], [75, 66, 4], [82, 29, 2]],
  },
  {
    id: "tool-drop",
    channel: "NIEZWERYFIKOWANY DROP",
    title: "SILENTSNIFF / ZERO TRACE",
    label: "RABAT KANAŁOWY",
    value: "-41%",
    stat: "9 KOPII POZOSTAŁO",
    timer: "02:06",
    cta: "SPRAWDŹ W GOOGLEPLEX",
    tone: "amber",
    layout: 3,
    radarSides: 5,
    nodes: [[18, 34, 3], [38, 21, 2], [43, 50, 4], [68, 35, 2], [76, 74, 3], [28, 76, 2]],
  },
  {
    id: "pvp-praga",
    channel: "SYGNAŁ WYSOKIEGO RYZYKA",
    title: "KONFLIKT / PRAGA PÓŁNOC",
    label: "AKTYWNOŚĆ PVP",
    value: "7x",
    stat: "3 CELE BEZ OSŁONY",
    timer: "01:47",
    cta: "WEJDŹ W STREFĘ",
    tone: "red",
    layout: 4,
    radarSides: 6,
    nodes: [[16, 48, 2], [29, 24, 3], [41, 67, 3], [57, 21, 2], [70, 55, 4], [83, 39, 3]],
  },
  {
    id: "leak-zoliborz",
    channel: "GHOST INTELLIGENCE",
    title: "PRZECIEK / ŻOLIBORZ",
    label: "WIARYGODNOŚĆ",
    value: "83%",
    stat: "11 WĘZŁÓW POWIĄZANYCH",
    timer: "06:24",
    cta: "OTWÓRZ DOSSIER",
    tone: "lime",
    layout: 5,
    radarSides: 7,
    nodes: [[14, 33, 2], [29, 61, 3], [43, 23, 2], [58, 57, 4], [72, 31, 2], [86, 69, 3]],
  },
  {
    id: "atm-srodmiescie",
    channel: "ALERT SYSTEMOWY",
    title: "ATM BURST / ŚRÓDMIEŚCIE",
    label: "OKNO OPERACJI",
    value: "90s",
    stat: "8 TERMINALI BEZ OSŁONY",
    timer: "00:58",
    cta: "NAMIERZ TERMINALE",
    tone: "cyan",
    layout: 6,
    radarSides: 8,
    nodes: [[17, 71, 3], [27, 38, 2], [46, 17, 3], [59, 46, 2], [71, 76, 4], [85, 28, 2]],
  },
];

function polygonPoints(sides: number, radius: number, rotation = -90) {
  return Array.from({ length: sides }, (_, index) => {
    const angle = ((rotation + index * 360 / sides) * Math.PI) / 180;
    return `${50 + Math.cos(angle) * radius},${50 + Math.sin(angle) * radius}`;
  }).join(" ");
}

function Radar({ signal }: { signal: Signal }) {
  const spokes = useMemo(() => Array.from({ length: 12 }, (_, i) => i * 30), []);
  const clipId = `radar-clip-${signal.id}`;
  const satellites = useMemo(() => signal.nodes.flatMap(([x, y], i) => [
    [Math.max(8, x - 7 + (i % 3) * 2), Math.min(92, y + 8), 0.45],
    [Math.min(92, x + 6), Math.max(8, y - 5 + (i % 2) * 3), 0.3],
  ]), [signal]);
  return (
    <svg className="radar" viewBox="0 0 100 100" role="img" aria-label={`Radar sygnału ${signal.title}`}>
      <defs>
        <clipPath id={clipId}>
          {signal.radarSides === 0
            ? <circle cx="50" cy="50" r="46" />
            : <polygon points={polygonPoints(signal.radarSides, 46, signal.radarSides === 4 ? -45 : -90)} />}
        </clipPath>
      </defs>
      <g className="radar-grid">
        {[12, 23, 34, 45].map((r) => signal.radarSides === 0
          ? <circle key={r} cx="50" cy="50" r={r} />
          : <polygon key={r} points={polygonPoints(signal.radarSides, r, signal.radarSides === 4 ? -45 : -90)} />
        )}
        {spokes.map((angle) => <line key={angle} x1="50" y1="50" x2="50" y2="4" transform={`rotate(${angle} 50 50)`} />)}
        <path clipPath={`url(#${clipId})`} d="M1 42 C20 30 29 55 42 37 S66 24 99 45 M3 66 C27 79 36 58 52 70 S72 80 97 62 M10 18 L31 31 L42 19 L57 35 L90 12" />
      </g>
      <g className="radar-frame">
        {signal.radarSides === 0
          ? <circle cx="50" cy="50" r="46" />
          : <polygon points={polygonPoints(signal.radarSides, 46, signal.radarSides === 4 ? -45 : -90)} />}
      </g>
      <g className={`radar-accent radar-shape-${signal.radarSides || "circle"}`}>
        {signal.radarSides === 0
          ? <circle cx="50" cy="50" r="39" />
          : <polygon points={polygonPoints(signal.radarSides, 39, signal.radarSides === 4 ? -45 : -90)} />}
      </g>
      <g className="radar-links">
        {signal.nodes.slice(1).map((n, i) => {
          const prev = signal.nodes[i];
          return <line key={i} x1={prev[0]} y1={prev[1]} x2={n[0]} y2={n[1]} />;
        })}
      </g>
      {signal.nodes.map(([x, y, r], i) => (
        <g key={`${x}-${y}`} className="radar-node" style={{ animationDelay: `${i * 170}ms` }}>
          <circle className="pulse-ring pulse-ring-a" cx={x} cy={y} r={r * 1.45} />
          <circle className="pulse-ring pulse-ring-b" cx={x} cy={y} r={r * 2.25} />
          <circle cx={x} cy={y} r={r / 1.9} />
          {i % 2 === 0 && <path d={`M${x - 2.5} ${y - 4} h5 v5 l-2.5 3 -2.5-3z`} />}
        </g>
      ))}
      <g className="radar-satellites">
        {satellites.map(([x, y, r], i) => <circle key={`${x}-${y}-${i}`} cx={x} cy={y} r={r} style={{ animationDelay: `${(i % 6) * 130}ms` }} />)}
      </g>
      <g className="radar-core">
        <circle cx="50" cy="50" r="8" /><circle cx="50" cy="50" r="4.5" /><circle cx="50" cy="50" r="1.3" />
      </g>
      <path clipPath={`url(#${clipId})`} className="radar-sweep" d="M50 50 L50 0 L92 4 Z" />
    </svg>
  );
}

export default function Home() {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState("right");
  const [captured, setCaptured] = useState(false);
  const dragStart = useRef<[number, number] | null>(null);
  const signal = signals[index];

  const move = (delta: number, dir: string) => {
    setDirection(dir);
    setCaptured(false);
    setIndex((current) => (current + delta + signals.length) % signals.length);
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (["ArrowRight", "ArrowDown", "d", "s"].includes(event.key)) move(1, event.key === "ArrowDown" || event.key === "s" ? "down" : "right");
      if (["ArrowLeft", "ArrowUp", "a", "w"].includes(event.key)) move(-1, event.key === "ArrowUp" || event.key === "w" ? "up" : "left");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const finishDrag = (x: number, y: number) => {
    if (!dragStart.current) return;
    const [sx, sy] = dragStart.current;
    const dx = x - sx;
    const dy = y - sy;
    dragStart.current = null;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 44) return;
    if (Math.abs(dx) > Math.abs(dy)) move(dx < 0 ? 1 : -1, dx < 0 ? "right" : "left");
    else move(dy < 0 ? 1 : -1, dy < 0 ? "down" : "up");
  };

  return (
    <main
      className={`blacknet tone-${signal.tone}`}
      onPointerDown={(e) => { dragStart.current = [e.clientX, e.clientY]; e.currentTarget.setPointerCapture(e.pointerId); }}
      onPointerUp={(e) => finishDrag(e.clientX, e.clientY)}
    >
      <div className="noise" />
      <header className="brand">
        <div className="brand-mark">BLACKNET</div>
        <div className="channel"><span>&gt;</span> {signal.channel}</div>
      </header>

      <div className="signal-strength" aria-label="Siła sygnału: mocna">
        <div className="bars"><i /><i /><i /><i /><i /></div>
        <span>SYGNAŁ: MOCNY</span>
      </div>

      <button className="nav nav-up" onClick={() => move(-1, "up")} aria-label="Poprzedni sygnał">⌃<span>PRZESUŃ W GÓRĘ</span></button>
      <button className="nav nav-down" onClick={() => move(1, "down")} aria-label="Następny sygnał">⌄<span>PRZESUŃ W DÓŁ</span></button>
      <button className="nav nav-left" onClick={() => move(-1, "left")} aria-label="Poprzedni sygnał">‹<span>PRZESUŃ W LEWO</span></button>
      <button className="nav nav-right" onClick={() => move(1, "right")} aria-label="Następny sygnał">›<span>PRZESUŃ W PRAWO</span></button>

      <section key={signal.id} className={`signal layout-${signal.layout} signal-enter-${direction}`}>
        <div className="copy">
          <h1>{signal.title}</h1>
          <div className="stat"><span className="target-icon">⊕</span>{signal.stat}</div>
          <div className="metric-label">{signal.label}</div>
          <div className="metric">{signal.value}</div>
        </div>
        <div className="visual"><Radar signal={signal} /></div>
        <div className="timer"><span className="hourglass">⌛</span><small>SYGNAŁ WAŻNY</small><strong>{signal.timer}</strong></div>
        <button className={`cta ${captured ? "captured" : ""}`} onClick={(e) => { e.stopPropagation(); setCaptured(true); }}>
          <span>⊕</span>{captured ? "SYGNAŁ PRZECHWYCONY" : signal.cta}
        </button>
      </section>

      <footer>
        <span>{String(index + 1).padStart(2, "0")} / {String(signals.length).padStart(2, "0")}</span>
        <span>SWIPE · WASD · STRZAŁKI</span>
        <span>BLACKNET SIGNAL BUS</span>
      </footer>
    </main>
  );
}
