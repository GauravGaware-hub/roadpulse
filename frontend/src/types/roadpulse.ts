// Mirrors backend/app/schemas.py

export type Classification = "STRONG_IMPACT" | "MODERATE_IMPACT" | "WEAK_IMPACT";
export type Level = "HIGH" | "MEDIUM" | "LOW";

export interface RoadEvent {
  id: number;
  start: number;
  end: number;
  duration: number;
  peak_time: number;
  peak_accel: number;
  event_median_accel: number | null;
  peak_prominence: number | null;
  peak_width: number | null;
  before_accel: number | null;
  after_accel: number | null;
  rise_rate: number | null;
  fall_rate: number | null;
  shape_balance: number | null;
  peak_gyro_near: number | null;
  speed: number | null;
  speed_band: string | null;
  latitude: number | null;
  longitude: number | null;
  impact_score: number;
  classification: Classification;
  hotspot_id: number | null;
}

export interface EventList {
  total: number;
  limit: number;
  offset: number;
  items: RoadEvent[];
}

export interface Hotspot {
  id: number;
  latitude: number;
  longitude: number;
  event_count: number;
  strong_events: number;
  moderate_events: number;
  max_impact_score: number;
  mean_impact_score: number;
  max_peak_accel: number;
  mean_peak_accel: number;
  first_event: number;
  last_event: number;
  confidence_level: Level;
  risk_level: Level;
}

export interface HotspotDetail extends Hotspot {
  events: RoadEvent[];
}

export interface HotspotList {
  total: number;
  items: Hotspot[];
}

export interface Stats {
  total_events: number;
  total_hotspots: number;
  strong_events: number;
  moderate_events: number;
  weak_events: number;
  highest_impact_score: number;
  events_with_gps: number;
  repeated_hotspots: number;
}

export interface IngestResult {
  status: "processed" | "failed";
  recording_id: string;
  rows_processed: number;
  duration_seconds: number;
  gps_rows: number;
  events_detected: number;
  hotspots_detected: number;
  files_used: string[];
  files_ignored: string[];
  recording_started: string | null;
  error: string | null;
  note: string;
  events: RoadEvent[];
  hotspots: Hotspot[];
}
