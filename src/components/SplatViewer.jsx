import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import * as GaussianSplats3D from "@mkkellogg/gaussian-splats-3d";

export default function SplatViewer({ plyUrl, onCapture }) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const rendererRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!plyUrl || !containerRef.current) return;

    let mounted = true;
    setReady(false);

    const container = containerRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      preserveDrawingBuffer: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const camera = new THREE.PerspectiveCamera(65, width / height, 0.1, 1000);
    camera.position.set(0, 0, 5);
    camera.up.set(0, -1, 0);
    camera.lookAt(0, 0, 0);

    const viewer = new GaussianSplats3D.Viewer({
      selfDrivenMode: true,
      renderer,
      camera,
      useBuiltInControls: true,
      rootElement: container,
      cameraUp: [0, -1, 0],
      initialCameraPosition: [0, 0, 5],
      initialCameraLookAt: [0, 0, 0],
      sharedMemoryForWorkers: false,
    });

    viewer
      .addSplatScene(plyUrl, {
        format: GaussianSplats3D.SceneFormat.Ply,
        splatAlphaRemovalThreshold: 5,
        showLoadingUI: false,
      })
      .then(() => {
        if (!mounted) return;
        viewer.start();
        requestAnimationFrame(() => {
          setTimeout(() => {
            if (mounted) setReady(true);
          }, 60);
        });
      })
      .catch((err) => {
        if (mounted) {
          console.error("Lỗi load splat scene:", err);
        }
      });

    viewerRef.current = viewer;

    return () => {
      mounted = false;
      if (viewerRef.current) {
        try {
          viewerRef.current.dispose();
        } catch (e) {}
        viewerRef.current = null;
      }
      if (rendererRef.current) {
        rendererRef.current.dispose();
        if (rendererRef.current.domElement?.parentNode) {
          rendererRef.current.domElement.parentNode.removeChild(
            rendererRef.current.domElement
          );
        }
        rendererRef.current = null;
      }
    };
  }, [plyUrl]);

  function handleCapture() {
    const renderer = rendererRef.current;
    if (!renderer) {
      alert("Chưa tìm thấy renderer, đợi model load xong đã nhé.");
      return;
    }
    const canvas = renderer.domElement;

    requestAnimationFrame(() => {
      const dataUrl = canvas.toDataURL("image/png");
      const shot = { id: Date.now(), dataUrl };
      onCapture?.(shot);
    });
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ position: "relative", flex: 1, minHeight: 0 }}>
        <div
          ref={containerRef}
          className={`splat-canvas-wrap ${ready ? "revealed" : ""}`}
        />
        {!ready && (
          <div className="splat-loading-overlay">
            <div className="splat-loading-ring" />
            <span>Đang dựng mô hình 3D...</span>
          </div>
        )}
      </div>

      {ready && (
        <div className="capture-bar">
          <button className="btn btn-primary" onClick={handleCapture}>
            📸 Chụp ảnh góc nhìn hiện tại
          </button>
          <span className="capture-hint">
            Xoay/kéo/zoom tới góc mong muốn rồi bấm chụp.
          </span>
        </div>
      )}
    </div>
  );
}