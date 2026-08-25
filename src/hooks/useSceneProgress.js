import { useEffect, useState } from "react";

export function useSceneProgress(sceneId, apiBase) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    if (!sceneId) return;

    const url = `${apiBase}/api/scenes/${sceneId}/progress`;
    const es = new EventSource(url);

    es.addEventListener("progress", (event) => {
      try {
        if (!event.data) return;
        const data = JSON.parse(event.data);
        setProgress(data);

        if (data.stage === "done" || data.stage === "error") {
          es.close();
        }
      } catch (err) {
        console.error("Lỗi parse progress event:", err, "raw:", event.data);
      }
    });

    es.onerror = (err) => {
      console.warn("SSE error (sẽ tự reconnect hoặc đóng):", err);
      // Không close ngay → để EventSource tự thử lại
    };

    return () => {
      es.close();
    };
  }, [sceneId, apiBase]);

  return progress;
}