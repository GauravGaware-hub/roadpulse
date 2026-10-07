import { PageHeader } from "../components/PageHeader";
import PipelineDiagram from "../components/PipelineDiagram";
import { Disclaimer } from "../components/States";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="card prose">
    <h3>{title}</h3>
    {children}
  </section>
);

export default function About() {
  return (
    <div className="stack">
      <PageHeader eyebrow="About" title="Turning Every Smartphone Into a Road-Health Sensor." subtitle="A research prototype for context-aware road-health monitoring from everyday smartphone motion data." />

      <div className="grid-2">
        <Section title="Problem">
          <p>
            Road surface damage is usually found through manual surveys, specialised inspection vehicles or citizen complaints. These are slow, costly and uneven. Millions of smartphones already travel on these roads carrying motion sensors and GPS, but a single
            vibration spike is ambiguous: it can be a pothole, a speed breaker, braking, a turn or traffic.
          </p>
        </Section>
        <Section title="Approach">
          <p>
            RoadPulse treats a detected impact as a <b>potential road anomaly</b>, not a diagnosis. It looks at the motion signature, the vehicle context and, above all, whether the same location produces repeated observations. Locations with repeated, strong
            impacts are ranked for inspection.
          </p>
        </Section>
      </div>

      <section className="card">
        <h3>How RoadPulse works</h3>
        <PipelineDiagram />
      </section>

      <div className="grid-2">
        <Section title="What makes RoadPulse different">
          <p>
            Smartphone road sensing is an established research area; RoadPulse does not claim to have invented it. The proposed contribution is the <i>combination</i> of:
          </p>
          <ul>
            <li>context-aware filtering of non-road motion</li>
            <li>road-specific baseline reasoning (speed-adaptive thresholds)</li>
            <li>repeated observations at the same place</li>
            <li>spatial aggregation into hotspots</li>
            <li>multi-vehicle confirmation (planned)</li>
            <li>maintenance-priority scoring</li>
          </ul>
        </Section>
        <Section title="Technology">
          <ul>
            <li>Sensor Logger recordings: accelerometer, gyroscope and GPS</li>
            <li>Python, pandas and NumPy signal processing</li>
            <li>Robust z-score event detection and impact-shape scoring</li>
            <li>DBSCAN spatial clustering (30 m, haversine)</li>
            <li>FastAPI backend, React, TypeScript and Leaflet frontend</li>
            <li>OpenStreetMap tiles (no map API key)</li>
          </ul>
        </Section>
        <Section title="Current capabilities">
          <ul>
            <li>Upload and process a real Sensor Logger recording</li>
            <li>Heuristic impact events graded strong, moderate or weak</li>
            <li>Repeated-hotspot clustering with exact GPS positions</li>
            <li>Heuristic confidence and inspection priority</li>
            <li>Dataset switching between the static Pune trip and uploaded recordings</li>
          </ul>
        </Section>
        <Section title="Future capabilities">
          <ul>
            <li>Context classification: normal, traffic, braking, turning, speed breaker, pothole</li>
            <li>Independent multi-vehicle confirmation</li>
            <li>Validated confidence scores per event</li>
            <li>Persistent storage and a fleet-scale ingestion service</li>
            <li>Maintenance dispatch integrations</li>
          </ul>
        </Section>
      </div>

      <Section title="Limitations">
        <ul>
          <li>The Pune data comes from one vehicle on one trip. Repeated hotspots are repeated impacts in that trip, not independent confirmation.</li>
          <li>Impact scores and classes are rule-based heuristics. They have not been validated against surveyed ground truth.</li>
          <li>
            There is no validated pothole classifier. Early research classifiers tested on unseen recordings performed poorly (three-class model: about 48% accuracy, macro F1 0.38) or only modestly (normal vs potential anomaly: about 63% accuracy, macro F1
            0.60). They are <b>not</b> used by this application.
          </li>
          <li>Context filtering currently covers only stopped-vehicle windows. Braking, turning and traffic are not yet separated from road impacts.</li>
          <li>GPS accuracy is not modelled; locations are used exactly as recorded.</li>
        </ul>
      </Section>
      <Disclaimer />
    </div>
  );
}
