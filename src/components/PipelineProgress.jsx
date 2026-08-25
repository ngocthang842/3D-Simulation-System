import { useEffect, useRef } from "react";
import { useSceneProgress } from "../hooks/useSceneProgress";

const API = "http://localhost:8000";

const STAGE_LABELS = {
  queued: "Đang chờ worker xử lý",
  frame_extraction: "Đang tách frame từ video",
  sfm: "Đang tính camera pose (SfM)",
  done: "Hoàn tất xử lý dataset",
  error: "Có lỗi xảy ra",
};

export default function PipelineProgress({ sceneId, onDone, onError }) {
  const progress = useSceneProgress(sceneId, API);
  const firedRef = useRef(false);

  useEffect(() => {
    if (!progress || firedRef.current) return;

    if (progress.stage === "done") {
      firedRef.current = true;
      onDone?.(progress);
    } else if (progress.stage === "error") {
      firedRef.current = true;
      onError?.(progress.message || "Pipeline bị lỗi");
    }
  }, [progress, onDone, onError]);

  if (!progress) {
    return (
      <div className="progress-card">
        <div className="progress-pulse-dot" />
        <p className="progress-label">Đang chờ tiến trình xử lý...</p>
      </div>
    );
  }

  const isError = progress.stage === "error";
  const pct = progress.progress || 0;
  const label = STAGE_LABELS[progress.stage] || progress.stage;

  return (
    <div className="progress-card">
      <div className="progress-track">
        <div
          className={`progress-fill ${isError ? "progress-fill-error" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="progress-label">
        <span className={`stage-chip ${isError ? "stage-chip-error" : ""}`}>
          {label}
        </span>
        <span className="progress-pct">{pct}%</span>
      </p>
      {progress.message && (
        <p className="progress-message">{progress.message}</p>
      )}
    </div>
  );
}