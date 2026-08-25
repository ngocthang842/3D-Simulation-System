import { useState, useEffect } from "react";
import SplatViewer from "./components/SplatViewer";
import PipelineProgress from "./components/PipelineProgress";
import "./App.css";

const API = "http://localhost:8000";
const STORAGE_KEY = "bts_scene_state";

export default function App() {
  const [sceneId, setSceneId] = useState(null);
  const [plyUrl, setPlyUrl] = useState(null);
  const [pipelineDone, setPipelineDone] = useState(false);
  const [datasetDownloaded, setDatasetDownloaded] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Ảnh chụp từ khung 3D - hiển thị ở cột thứ 3
  const [shots, setShots] = useState([]);
  const [selectedShot, setSelectedShot] = useState(null);

  // Khôi phục state
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        if (data.sceneId) setSceneId(data.sceneId);
        if (data.plyUrl) setPlyUrl(data.plyUrl);
        if (data.pipelineDone) setPipelineDone(data.pipelineDone);
        if (data.datasetDownloaded) setDatasetDownloaded(data.datasetDownloaded);
        if (data.uploadedFileName) setUploadedFileName(data.uploadedFileName);
      } catch (e) {
        console.error("Lỗi đọc trạng thái đã lưu:", e);
        localStorage.removeItem(STORAGE_KEY);
      }
    }
  }, []);

  // Lưu state
  useEffect(() => {
    if (sceneId) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          sceneId,
          plyUrl,
          pipelineDone,
          datasetDownloaded,
          uploadedFileName,
        })
      );
    }
  }, [sceneId, plyUrl, pipelineDone, datasetDownloaded, uploadedFileName]);

  function handleReset() {
    localStorage.removeItem(STORAGE_KEY);
    setSceneId(null);
    setPlyUrl(null);
    setPipelineDone(false);
    setDatasetDownloaded(false);
    setUploadedFileName("");
    setError(null);
    setShots([]);
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API}/api/scenes`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Upload thất bại (${res.status}): ${errText}`);
      }

      const data = await res.json();
      if (!data.scene_id) throw new Error("Backend không trả về scene_id");

      // Reset hết state cũ
      setSceneId(data.scene_id);
      setPlyUrl(null);
      setPipelineDone(false);
      setDatasetDownloaded(false);
      setUploadedFileName(file.name);
      setShots([]);
    } catch (err) {
      console.error(err);
      setError(err.message || "Upload thất bại. Kiểm tra backend đang chạy chưa.");
    } finally {
      setUploading(false);
      // reset input để chọn lại cùng file được
      e.target.value = "";
    }
  }

  async function handleUploadPly(e) {
    const file = e.target.files?.[0];
    if (!file || !sceneId) return;

    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API}/api/scenes/${sceneId}/upload-ply`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload .ply thất bại");

      // Thêm timestamp để tránh cache
      setPlyUrl(`${API}/api/scenes/${sceneId}/model.ply?t=${Date.now()}`);
      setShots([]);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      e.target.value = "";
    }
  }

  async function handleDownloadDataset() {
    if (!sceneId) return;
    setDownloading(true);
    setError(null);

    try {
      const res = await fetch(`${API}/api/scenes/${sceneId}/download-dataset`);
      if (!res.ok) {
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          const err = await res.json();
          throw new Error(err.error || "Chưa có dataset");
        }
        throw new Error("Tải dataset thất bại");
      }

      const blob = await res.blob();
      const filename = `dataset_${sceneId}.zip`;

      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: filename,
            types: [{ description: "Zip file", accept: { "application/zip": [".zip"] } }],
          });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          setDatasetDownloaded(true);
          return;
        } catch (err) {
          if (err.name === "AbortError") return;
          console.error(err);
        }
      }

      // Fallback
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setDatasetDownloaded(true);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  function handleCaptureShot(shot) {
    setShots((prev) => [shot, ...prev]); // ảnh mới nhất lên đầu
  }

  function handleDownloadShot(shot) {
    const a = document.createElement("a");
    a.href = shot.dataUrl;
    a.download = `novel_view_${shot.id}.png`;
    a.click();
  }

  // Đóng modal xem ảnh full bằng Esc
  useEffect(() => {
    if (!selectedShot) return;
    function onKeyDown(e) {
      if (e.key === "Escape") setSelectedShot(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedShot]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-eyebrow">3D Gaussian Splatting Pipeline</span>
          <h1 className="brand-title">Digital Twin</h1>
        </div>
        {sceneId && (
          <button className="btn btn-ghost" onClick={handleReset}>
            Làm lại từ đầu
          </button>
        )}
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button className="error-close" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="layout-grid">
        {/* CỘT 1 - Pipeline */}
        <aside className="col-left glass-card">
          <div className="step-block">
            <div className="step-head">
              <div className={`step-number ${sceneId ? "step-done" : ""}`}>
                {sceneId ? "✓" : "1"}
              </div>
              <div>
                <p className="step-title">Upload video / ảnh drone</p>
              </div>
            </div>

            <label className="upload-zone">
              <input type="file" onChange={handleUpload} disabled={uploading} />
              <div className="upload-zone-label">
                {uploading
                  ? "Đang upload..."
                  : uploadedFileName
                  ? <><strong>{uploadedFileName}</strong> — bấm để đổi tệp</>
                  : <>Kéo thả hoặc <strong>bấm để chọn</strong> video / ảnh drone</>}
              </div>
            </label>

            {sceneId && <div className="scene-id-chip">{sceneId}</div>}

            {sceneId && (
              <PipelineProgress
                sceneId={sceneId}
                onDone={() => setPipelineDone(true)}
                onError={(msg) => setError(msg)}
              />
            )}
          </div>

          {pipelineDone && (
            <div className="step-block">
              <div className="dataset-ready-box">
                <span className="dataset-ready-text">Dataset đã sẵn sàng.</span>
                <button className="btn btn-primary" onClick={handleDownloadDataset} disabled={downloading}>
                  {downloading ? "Đang đóng gói..." : "Tải dataset"}
                </button>
              </div>
              {datasetDownloaded && (
                <div className="success-banner">
                  Đã tải xong
                </div>
              )}
            </div>
          )}

          {pipelineDone && (
            <div className="step-block">
              <div className="step-head">
                <div className={`step-number ${plyUrl ? "step-done" : ""}`}>
                  {plyUrl ? "✓" : "2"}
                </div>
                <div>
                  <p className="step-title">Upload model đã train</p>

                </div>
              </div>
              <label className="upload-zone">
                <input type="file" accept=".ply" onChange={handleUploadPly} />
                <div className="upload-zone-label">
                  Kéo thả hoặc <strong>bấm để chọn</strong> file .ply
                </div>
              </label>
            </div>
          )}
        </aside>

        {/* CỘT 2 - 3D Viewer */}
        <main className="col-center glass-card viewer-card">
          <div className="viewer-header">
            <span className="pill pill-cyan">3D View</span>
            {plyUrl && <span className="pill pill-green">Sẵn sàng</span>}
          </div>
          <div className="viewer-body">
            {plyUrl ? (
              <SplatViewer plyUrl={plyUrl} onCapture={handleCaptureShot} />
            ) : (
              <div className="viewer-placeholder">
                Model 3D sẽ hiển thị
              </div>
            )}
          </div>
        </main>

        {/* CỘT 3 - Ảnh đã chụp, mỗi ảnh 1 hàng */}
        <aside className="col-shots glass-card">
          <h2 className="col-title">Ảnh đã chụp</h2>
          {shots.length === 0 ? (
            <p className="shots-empty">Chụp ảnh từ khung 3D bên cạnh, ảnh sẽ hiện ở đây.</p>
          ) : (
            <div className="shot-list">
              {shots.map((shot) => (
                <div key={shot.id} className="shot-row">
                  <img
                    src={shot.dataUrl}
                    alt="novel view"
                    className="shot-row-thumb"
                    onClick={() => setSelectedShot(shot)}
                  />
                  <button
                    className="btn shot-download-btn"
                    onClick={() => handleDownloadShot(shot)}
                  >
                    Tải ảnh này
                  </button>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>

      {selectedShot && (
        <div className="modal-backdrop" onClick={() => setSelectedShot(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <img src={selectedShot.dataUrl} alt="novel view full" className="modal-img" />
            <div style={{ display: "flex", gap: 12 }}>
              <button className="btn btn-primary" onClick={() => handleDownloadShot(selectedShot)}>
                ⬇️ Tải ảnh về
              </button>
              <button className="btn" onClick={() => setSelectedShot(null)}>
                ✕ Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}