const PATHS = {
  overview: "M3 3h7v9H3z M14 3h7v5h-7z M14 12h7v9h-7z M3 16h7v5H3z",
  map: "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z M9 4v14 M15 6v14",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7z",
  hotspot: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  upload: "M12 16V4 M7 9l5-5 5 5 M4 20h16",
  chart: "M4 20V10 M10 20V4 M16 20v-8 M22 20H2",
  play: "M7 4v16l13-8z",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 11v5 M12 8h.01",
  settings: "M4 6h9 M17 6h3 M4 12h3 M11 12h9 M4 18h11 M19 18h1 M15 4v4 M9 10v4 M17 16v4",
  menu: "M4 6h16 M4 12h16 M4 18h16",
  x: "M6 6l12 12 M18 6 6 18",
  alert: "M12 3 2 20h20z M12 10v4 M12 17h.01",
  check: "M5 12l5 5 9-11",
  pin: "M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z M12 7a2 2 0 1 0 0 4 2 2 0 0 0 0-4z",
  arrow: "M5 12h14 M13 6l6 6-6 6",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7 M20 4v7h-7",
  file: "M6 3h8l4 4v14H6z M14 3v4h4",
  layers: "M12 3 3 8l9 5 9-5z M3 13l9 5 9-5",
  pulse: "M2 12h4l3-8 4 16 3-8h6",
  fit: "M4 9V4h5 M20 9V4h-5 M4 15v5h5 M20 15v5h-5",
  reset: "M4 4v6h6 M5.5 15a8 8 0 1 0 2-8.5L4 10",
  database: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3z M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6 M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6",
} as const;

export type IconName = keyof typeof PATHS;

export default function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
