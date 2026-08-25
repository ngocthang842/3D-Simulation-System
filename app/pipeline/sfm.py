import pycolmap
from pathlib import Path
from typing import Optional, Callable
import shutil


def run_colmap(
    images_dir: Path,
    sparse_dir: Path,
    progress_cb: Optional[Callable[[int], None]] = None
) -> Path:
    """
    Chạy full pipeline SfM bằng PyCOLMAP.

    Input:
        traincolab/
        └── images/
            ├── 00000.jpg
            ├── 00001.jpg
            ├── 00002.jpg
            └── ...

    Output:
        traincolab/
        ├── images/
        │   ├── 00000.jpg
        │   ├── 00001.jpg
        │   └── ...
        │
        └── sparse/
            └── 0/
                ├── cameras.txt
                ├── images.txt
                └── points3D.txt
    """

    images_dir = Path(images_dir)
    sparse_dir = Path(sparse_dir)

    # ==============================
    # 1. KIỂM TRA THƯ MỤC ẢNH
    # ==============================

    if not images_dir.exists():
        raise FileNotFoundError(
            f"Không tìm thấy thư mục ảnh: {images_dir}"
        )

    image_files = sorted([
        p for p in images_dir.iterdir()
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ])

    if len(image_files) == 0:
        raise RuntimeError(
            f"Không tìm thấy ảnh trong: {images_dir}"
        )

    print("=" * 60)
    print("[COLMAP] Input images:")
    print(f"         {images_dir}")
    print(f"         Số lượng ảnh: {len(image_files)}")
    print("=" * 60)

    # ==============================
    # 2. TẠO THƯ MỤC SPARSE
    # ==============================

    sparse_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    database_path = sparse_dir / "database.db"
    output_model_dir = sparse_dir / "0"

    # Nếu database cũ tồn tại thì xóa
    # để COLMAP tạo lại từ đầu
    if database_path.exists():
        print("[COLMAP] Xóa database cũ...")
        database_path.unlink()

    # Nếu reconstruction cũ tồn tại thì xóa
    if output_model_dir.exists():
        print("[COLMAP] Xóa reconstruction cũ...")

        shutil.rmtree(output_model_dir)

    output_model_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ==============================
    # 3. FEATURE EXTRACTION
    # ==============================

    print("\n[COLMAP] Extracting features...")

    # QUAN TRỌNG:
    # Bắt buộc dùng PINHOLE
    reader_options = pycolmap.ImageReaderOptions()

    reader_options.camera_model = "PINHOLE"

    pycolmap.extract_features(
        database_path=str(database_path),
        image_path=str(images_dir),

        # Vì toàn bộ frame đến từ cùng một camera/video
        # nên dùng chung một camera
        camera_mode=pycolmap.CameraMode.SINGLE,

        reader_options=reader_options,
    )

    print("[COLMAP] Feature extraction completed.")

    if progress_cb:
        progress_cb(30)

    # ==============================
    # 4. FEATURE MATCHING
    # ==============================

    print("\n[COLMAP] Matching features...")

    pycolmap.match_exhaustive(
        database_path=str(database_path)
    )

    print("[COLMAP] Feature matching completed.")

    if progress_cb:
        progress_cb(60)

    # ==============================
    # 5. INCREMENTAL MAPPING
    # ==============================

    print("\n[COLMAP] Running incremental mapping...")

    maps = pycolmap.incremental_mapping(
        database_path=str(database_path),
        image_path=str(images_dir),
        output_path=str(sparse_dir),
    )

    if not maps:
        raise RuntimeError(
            "COLMAP không tạo được reconstruction nào.\n"
            "Hãy kiểm tra:\n"
            "- Ảnh có đủ đặc trưng không\n"
            "- Các frame có quá giống nhau không\n"
            "- Camera có di chuyển không\n"
            "- Có đủ overlap giữa các frame không"
        )

    print(f"[COLMAP] Tạo được {len(maps)} reconstruction.")

    # ==============================
    # 6. CHỌN RECONSTRUCTION TỐT NHẤT
    # ==============================

    reconstruction = maps[0]

    print(
        f"[COLMAP] Reconstruction có "
        f"{reconstruction.num_images()} images"
    )

    print(
        f"[COLMAP] Reconstruction có "
        f"{reconstruction.num_points3D()} points3D"
    )

    # ==============================
    # 7. GHI FORMAT TEXT
    # ==============================

    reconstruction.write_text(
        str(output_model_dir)
    )

    # ==============================
    # 8. KIỂM TRA CAMERA MODEL
    # ==============================

    cameras_file = output_model_dir / "cameras.txt"

    print("\n" + "=" * 60)
    print("[COLMAP] CAMERA MODEL")
    print("=" * 60)

    models = set()

    with open(cameras_file, "r") as f:
        for line in f:

            if not line.strip():
                continue

            if line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) >= 2:
                models.add(parts[1])

                print(line.strip())

    print("=" * 60)

    if models == {"PINHOLE"}:
        print("✓ Camera model = PINHOLE")
    else:
        print("⚠ Camera model:", models)

    # ==============================
    # 9. KIỂM TRA FILE OUTPUT
    # ==============================

    print("\n" + "=" * 60)
    print("[COLMAP] OUTPUT")
    print("=" * 60)

    required_files = [
        "cameras.txt",
        "images.txt",
        "points3D.txt",
    ]

    for filename in required_files:

        filepath = output_model_dir / filename

        if filepath.exists():
            print(f"✓ {filename}")
        else:
            print(f"✗ THIẾU {filename}")

    print("=" * 60)

    if progress_cb:
        progress_cb(100)

    print(
        f"\n[COLMAP] Thành công!\n"
        f"Output: {output_model_dir}"
    )

    return output_model_dir