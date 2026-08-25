"""Bước 1: tách frame từ video drone bằng OpenCV."""
import cv2
from pathlib import Path


def extract(video_path: str, out_dir: Path, fps: int = 2) -> int:
    """
    Tách frame theo tốc độ fps mong muốn (không phải fps gốc của video).
    Nếu input là folder ảnh sẵn (zip ảnh) thì bỏ qua bước này, copy thẳng.
    Trả về số lượng ảnh tách được.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if Path(video_path).is_dir():
        # input là folder ảnh sẵn (trường hợp đề bài cho sẵn 100-300 ảnh)
        import shutil
        count = 0
        for img in sorted(Path(video_path).glob("*.*")):
            shutil.copy(img, out_dir / img.name)
            count += 1
        return count

    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = max(1, round(video_fps / fps))

    frame_idx, saved_idx = 0, 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            out_path = out_dir / f"frame_{saved_idx:05d}.jpg"
            cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_idx += 1
        frame_idx += 1

    cap.release()
    return saved_idx
