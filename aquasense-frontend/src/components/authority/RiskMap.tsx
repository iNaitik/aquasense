import { useEffect, useMemo, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  useMap,
} from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import "leaflet/dist/leaflet.css";
import type { PipelineListItem } from "@/lib/api";
import { riskColor } from "@/lib/api";

const INDORE_CENTER: [number, number] = [22.7196, 75.8577];

function FocusOn({ pipeline }: { pipeline: PipelineListItem | null }) {
  const map = useMap();
  useEffect(() => {
    if (!pipeline) return;
    const bounds: LatLngBoundsExpression = [
      [pipeline.start_latitude, pipeline.start_longitude],
      [pipeline.end_latitude, pipeline.end_longitude],
    ];
    map.flyToBounds(bounds, { padding: [80, 80], maxZoom: 16, duration: 0.8 });
  }, [pipeline, map]);
  return null;
}

interface RiskMapProps {
  pipelines: PipelineListItem[];
  selectedId: string | null;
  onSelect: (p: PipelineListItem) => void;
  focusPipeline: PipelineListItem | null;
}

export default function RiskMap({
  pipelines,
  selectedId,
  onSelect,
  focusPipeline,
}: RiskMapProps) {
  const initialized = useRef(false);
  // Ensure MapContainer only mounts once
  const key = useMemo(() => "authority-risk-map", []);

  // sort so HIGH renders on top
  const sorted = useMemo(() => {
    const order: Record<string, number> = { LOW: 0, MEDIUM: 1, HIGH: 2 };
    return [...pipelines].sort(
      (a, b) => (order[a.risk_level] ?? 0) - (order[b.risk_level] ?? 0),
    );
  }, [pipelines]);

  useEffect(() => {
    initialized.current = true;
  }, []);

  return (
    <MapContainer
      key={key}
      center={INDORE_CENTER}
      zoom={12}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {sorted.map((p) => {
        const isSelected = p.pipeline_id === selectedId;
        return (
          <Polyline
            key={p.pipeline_id}
            positions={[
              [p.start_latitude, p.start_longitude],
              [p.end_latitude, p.end_longitude],
            ]}
            pathOptions={{
              color: riskColor(p.risk_level),
              weight: isSelected ? 8 : p.risk_level === "HIGH" ? 5 : 3.5,
              opacity: isSelected ? 1 : 0.85,
            }}
            eventHandlers={{
              click: () => onSelect(p),
            }}
          />
        );
      })}
      <FocusOn pipeline={focusPipeline} />
    </MapContainer>
  );
}
