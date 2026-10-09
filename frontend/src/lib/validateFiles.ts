// Client-side checks that run BEFORE any upload, using only the first few KB of each file.
// They mirror what the backend requires so mistakes are caught instantly instead of after a large upload.

export interface Issue {
  field: string;
  level: "error" | "warn";
  message: string;
}

const LABEL: Record<string, string> = {
  accelerometer: "Accelerometer.csv",
  gyroscope: "Gyroscope.csv",
  location: "Location.csv",
  total_acceleration: "TotalAcceleration.csv",
  metadata: "Metadata.csv",
};
const REQUIRED_COLS: Record<string, string[]> = {
  accelerometer: ["seconds_elapsed", "x", "y", "z"],
  gyroscope: ["seconds_elapsed", "x", "y", "z"],
  location: ["seconds_elapsed", "latitude", "longitude", "speed"],
  total_acceleration: ["seconds_elapsed"],
};
const REQUIRED_FIELDS = ["accelerometer", "gyroscope", "location"];
const MAX_FILE_BYTES = 200 * 1024 * 1024; // backend limit per file
// First GPS fix can legitimately lag the motion sensors (e.g. recording started indoors), so only a gap of
// hours is treated as "different recordings" (error); 5 minutes to 1 hour is just a warning.
const MIXED_ERROR_S = 3600;
const MIXED_WARN_S = 300;

const clean = (s: string) => s.replace(/^﻿/, "").trim().replace(/^"|"$/g, "");

/** Parse the header and the first data row from the start of a file. */
async function peek(file: File): Promise<{ cols: string[]; first: Record<string, string> }> {
  const text = await file.slice(0, 8192).text();
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  const cols = (lines[0] ?? "").split(",").map(clean);
  const vals = (lines[1] ?? "").split(",").map(clean);
  const first: Record<string, string> = {};
  cols.forEach((c, i) => (first[c] = vals[i] ?? ""));
  return { cols, first };
}

/** Sensor Logger `time` is an epoch in ns (sometimes us/ms). Returns seconds, or null if unusable. */
function epochSeconds(v: string | undefined): number | null {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return null;
  if (n > 1e17) return n / 1e9;
  if (n > 1e14) return n / 1e6;
  if (n > 1e11) return n / 1e3;
  return null;
}

export async function validateSelection(files: Record<string, File>): Promise<Issue[]> {
  const issues: Issue[] = [];
  const add = (field: string, level: Issue["level"], message: string) => issues.push({ field, level, message });

  for (const f of REQUIRED_FIELDS) if (!files[f]) add(f, "error", `${LABEL[f]} is required.`);

  const firstTimes: Record<string, number> = {};
  for (const [field, file] of Object.entries(files)) {
    const label = LABEL[field] ?? file.name;
    if (!/\.csv$/i.test(file.name)) add(field, "error", `${label}: "${file.name}" is not a .csv file.`);
    if (file.size === 0) {
      add(field, "error", `${label} is empty (0 bytes).`);
      continue;
    }
    if (file.size > MAX_FILE_BYTES) add(field, "error", `${label} is ${(file.size / 1048576).toFixed(0)} MB; the limit is 200 MB per file.`);
    if (/uncalibrated/i.test(file.name)) add(field, "warn", `${label}: "${file.name}" looks like an Uncalibrated sensor file. RoadPulse expects the plain ${label}.`);

    const need = REQUIRED_COLS[field];
    if (!need) continue; // metadata: nothing required
    try {
      const { cols, first } = await peek(file);
      const missing = need.filter((c) => !cols.includes(c));
      if (missing.length) {
        const looksLikeLocation = cols.includes("latitude") && cols.includes("longitude");
        add(field, "error", `${label} is missing column${missing.length > 1 ? "s" : ""} ${missing.join(", ")}.${looksLikeLocation && field !== "location" ? " This looks like a Location file." : " Is this the right file?"}`);
      } else {
        const t = epochSeconds(first["time"]);
        if (t !== null && REQUIRED_FIELDS.includes(field)) firstTimes[field] = t;
      }
    } catch {
      add(field, "error", `${label} could not be read. Try selecting it again.`);
    }
  }

  // Files from different recordings would never line up in time
  const ts = Object.values(firstTimes);
  if (ts.length >= 2) {
    const gap = Math.max(...ts) - Math.min(...ts);
    if (gap > MIXED_ERROR_S) add("accelerometer", "error", "These files appear to come from different recordings (their start times differ by more than an hour). Select the files from one Sensor Logger export.");
    else if (gap > MIXED_WARN_S) add("accelerometer", "warn", `Note: the files start ${Math.round(gap / 60)} minutes apart. That is normal if the GPS fix was slow, but if they are not from the same recording the results will be wrong. Upload continues.`);
  }
  return issues;
}
