"""
Backend chính - FastAPI
Chạy: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sse_starlette.sse import EventSourceResponse

from app.workers.tasks import run_pipeline
from app.core.redis_client import redis_client

app = FastAPI(title="BTS Digital Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path("./data/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/scenes")
async def create_scene(file: UploadFile = File(...)):
    scene_id = str(uuid.uuid4())
    scene_dir = UPLOAD_DIR / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)

    dest_path = scene_dir / file.filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    run_pipeline.delay(scene_id=scene_id, input_path=str(dest_path))

    return {"scene_id": scene_id, "status": "queued"}


@app.get("/api/scenes/{scene_id}/progress")
async def scene_progress(scene_id: str):
    async def event_generator():
        import asyncio
        import json

        pubsub = redis_client.pubsub()
        channel = f"progress:{scene_id}"
        pubsub.subscribe(channel)

        # Gửi event đầu tiên ngay lập tức
        yield {
            "event": "progress",
            "data": json.dumps({
                "stage": "queued",
                "progress": 0,
                "message": "Đã vào hàng đợi, đang chờ worker..."
            })
        }

        try:
            while True:
                message = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0
                    )
                )

                if message and message.get("type") == "message":
                    raw = message["data"]

                    if isinstance(raw, bytes):
                        data_str = raw.decode("utf-8")
                    else:
                        data_str = str(raw)

                    try:
                        json.loads(data_str)
                    except Exception:
                        continue

                    yield {
                        "event": "progress",
                        "data": data_str
                    }

                    if '"stage": "done"' in data_str or '"stage": "error"' in data_str:
                        break

                await asyncio.sleep(0.1)
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except Exception:
                pass

    return EventSourceResponse(event_generator())


@app.get("/api/scenes/{scene_id}/download-dataset")
async def download_dataset(scene_id: str):
    """
    Đóng gói images/ + sparse/ thành file .zip để tải về train trên Colab.
    """
    scene_out = OUTPUT_DIR / scene_id
    images_dir = scene_out / "images"
    sparse_dir = scene_out / "sparse"

    if not images_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="Chưa có dataset. Đợi bước tách frame + SfM xử lý xong đã nhé."
        )

    zip_path = scene_out / "dataset.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in images_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f"images/{f.relative_to(images_dir)}")
        if sparse_dir.exists():
            for f in sparse_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=f"sparse/{f.relative_to(sparse_dir)}")

    return FileResponse(
        path=zip_path,
        filename=f"dataset_{scene_id}.zip",
        media_type="application/zip",
    )


@app.post("/api/scenes/{scene_id}/upload-ply")
async def upload_ply(scene_id: str, file: UploadFile = File(...)):
    """
    Nhận file model.ply (hoặc point_cloud.ply) sau khi train xong trên Colab.
    Lưu vào data/outputs/{scene_id}/ và trả về URL để frontend load vào SplatViewer.
    """
    if not file.filename.lower().endswith(".ply"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .ply")

    scene_out = OUTPUT_DIR / scene_id
    scene_out.mkdir(parents=True, exist_ok=True)

    # Lưu với tên cố định để dễ lấy lại
    dest_path = scene_out / "point_cloud.ply"

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Trả về URL để frontend dùng
    ply_url = f"/api/scenes/{scene_id}/ply"

    return {
        "scene_id": scene_id,
        "filename": file.filename,
        "ply_url": ply_url,
        "message": "Upload .ply thành công"
    }


@app.get("/api/scenes/{scene_id}/model.ply")
async def get_ply(scene_id: str):
    """Serve file .ply cho SplatViewer"""
    ply_path = OUTPUT_DIR / scene_id / "point_cloud.ply"

    if not ply_path.exists():
        raise HTTPException(status_code=404, detail="Chưa có file .ply cho scene này")

    return FileResponse(
        path=ply_path,
        filename="model.ply",
        media_type="application/octet-stream",
    )


@app.get("/")
async def root():
    return {"status": "ok", "message": "BTS Digital Twin API đang chạy"}