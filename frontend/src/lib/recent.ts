// Remembers recordings processed in THIS browser so they can be reopened. Only small summary fields are kept
// (the results themselves live on the server). Storage may be unavailable; everything degrades to "no history".

export interface RecentRecording {
  id: string;
  savedAt: number; // ms epoch
  rows: number;
  events: number;
  hotspots: number;
}

const KEY = "roadpulse.recentRecordings";
const MAX = 5;

export function loadRecent(): RecentRecording[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((r) => typeof r?.id === "string").slice(0, MAX) : [];
  } catch {
    return [];
  }
}

function save(list: RecentRecording[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
  } catch {
    /* storage unavailable */
  }
}

export function addRecent(r: RecentRecording): RecentRecording[] {
  const list = [r, ...loadRecent().filter((x) => x.id !== r.id)].slice(0, MAX);
  save(list);
  return list;
}

export function removeRecent(id: string): RecentRecording[] {
  const list = loadRecent().filter((x) => x.id !== id);
  save(list);
  return list;
}
