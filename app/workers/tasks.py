"""
Task chạy trên máy có GPU. Đây là nơi gọi tuần tự:
OpenCV (tách frame) -> pycolmap (SfM) -> gsplat/gaussian-splatting (train) -> render target
Mỗi bước xong publish trạng thái vào Redis để backend forward qua SSE.
"""
import json
from pathlib import Path

from app.workers.celery_app import celery_app
from app.core.redis_client import redis_client
from app.pipeline import frame_extraction, sfm, render_target

# Sửa đường dẫn cho đúng với máy Windows của bạn
from pathlib import Path
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "outputs"


def publish(scene_id: str, stage: str, progress: float, message: str = ""):
    """Gửi 1 event tiến trình lên Redis channel riêng của scene đó."""
    payload = json.dumps({"stage": stage, "progress": progress, "message": message})
    redis_client.publish(f"progress:{scene_id}", payload)


@celery_app.task(bind=True)
def run_pipeline(self, scene_id: str, input_path: str):
    scene_out = OUTPUT_DIR / scene_id
    scene_out.mkdir(parents=True, exist_ok=True)

    try:
        # === Bước 1: Frame extraction ===
        publish(scene_id, "frame_extraction", 0, "Đang tách frame từ video...")
        images_dir = scene_out / "images"
        n_frames = frame_extraction.extract(input_path, images_dir, fps=2)
        publish(scene_id, "frame_extraction", 100, f"Tách được {n_frames} ảnh")

        # === Bước 2: SfM (COLMAP/pycolmap) ===
        publish(scene_id, "sfm", 0, "Đang tính camera pose (SfM)...")
        sparse_dir = scene_out / "sparse"

        model_dir = sfm.run_colmap(
            images_dir,
            sparse_dir,
            progress_cb=lambda p: publish(scene_id, "sfm", p)
        )

        publish(scene_id, "sfm", 100, "Tính pose xong")

        # Train 3DGS chạy trên Colab (có GPU) - không chạy ở đây.
        publish(
            scene_id,
            "done",
            100,
            "Xong bước SfM. Tải images/ + sparse/ lên Colab để train."
        )

        # === Quan trọng: phải return ===
        return {
            "scene_id": scene_id,
            "status": "sfm_completed",
            "images_dir": str(images_dir),
            "sparse_dir": str(model_dir),
            "message": "Sẵn sàng mang lên Colab train"
        }

    except Exception as e:
        publish(scene_id, "error", 0, str(e))
        raise


@celery_app.task(bind=True)
def render_target_poses(self, scene_id: str, poses: list[dict]):
    """
    Task riêng, chạy SAU khi đã train xong - chỉ render, không train lại.
    """
    model_dir = OUTPUT_DIR / scene_id
    out_dir = model_dir / "novel_views"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        publish(scene_id, "rendering", 0, f"Đang render {len(poses)} góc nhìn mục tiêu...")
        paths = render_target.render_poses(
            model_dir=model_dir,
            poses=poses,
            output_dir=out_dir,
            progress_cb=lambda i, total: publish(
                scene_id, "rendering", round(i / total * 100, 1)
            ),
        )
        publish(scene_id, "render_done", 100, f"Đã render {len(paths)} ảnh")
        return paths
    except Exception as e:
        publish(scene_id, "error", 0, str(e))
        raise