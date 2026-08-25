"""
Bước 2: SfM - tính camera pose bằng pycolmap.
Nếu đề bài đã cho sẵn pose (cameras.txt/images.txt), BỎ QUA hàm run_colmap này,
gọi thẳng skip_if_pose_given() để convert format đề cho sang chuẩn COLMAP.
"""
import pycolmap
from pathlib import Path


def run_colmap(images_dir: Path, sparse_dir: Path, progress_cb=None):
    """Chạy full pipeline SfM: feature extraction -> matching -> mapping."""
    sparse_dir.mkdir(parents=True, exist_ok=True)
    database_path = sparse_dir / "database.db"

    pycolmap.extract_features(str(database_path), str(images_dir))
    if progress_cb:
        progress_cb(33)

    pycolmap.match_exhaustive(str(database_path))
    if progress_cb:
        progress_cb(66)

    maps = pycolmap.incremental_mapping(
        str(database_path), str(images_dir), str(sparse_dir)
    )
    # maps[0] là reconstruction chính, export ra format text chuẩn
    maps[0].write_text(str(sparse_dir / "0"))
    if progress_cb:
        progress_cb(100)


def skip_if_pose_given(pose_json_path: Path, sparse_dir: Path):
    """
    Dùng khi đề bài đã cho sẵn pose (không cần chạy COLMAP).
    Đọc file JSON pose của đề, ghi ra đúng format cameras.txt/images.txt/points3D.txt
    mà gaussian-splatting repo cần.
    """
    import json

    sparse_out = sparse_dir / "0"
    sparse_out.mkdir(parents=True, exist_ok=True)

    with open(pose_json_path) as f:
        data = json.load(f)

    # TODO: viết logic convert cụ thể theo đúng format JSON mà đề bài BTS cung cấp
    # (cần xem mẫu file thật của đề để biết field tên gì - fx/fy/cx/cy, quaternion hay matrix)
    raise NotImplementedError(
        "Cần format mẫu file pose thật của đề bài để viết converter chính xác"
    )
