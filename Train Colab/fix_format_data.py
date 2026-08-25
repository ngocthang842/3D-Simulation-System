import os
import shutil
import re

# ==============================
# ĐƯỜNG DẪN DATASET
# ==============================

base = "/content/drive/MyDrive/traincolab"
sparse = os.path.join(base, "sparse", "0")
images_dir = os.path.join(base, "images")

cameras_txt = os.path.join(sparse, "cameras.txt")
images_txt = os.path.join(sparse, "images.txt")

print("Dataset:", base)
print("Sparse :", sparse)
print("Images :", images_dir)


# ==============================
# 1. BACKUP FILE GỐC
# ==============================

shutil.copy2(
    cameras_txt,
    cameras_txt + ".backup"
)

shutil.copy2(
    images_txt,
    images_txt + ".backup"
)

print("\n✓ Đã backup cameras.txt")
print("✓ Đã backup images.txt")


# ==============================
# 2. CHUYỂN SIMPLE_PINHOLE
#    -> PINHOLE
# ==============================

new_camera_lines = []

with open(cameras_txt, "r") as f:
    for line in f:

        stripped = line.strip()

        # Giữ nguyên comment
        if not stripped or stripped.startswith("#"):
            new_camera_lines.append(line)
            continue

        parts = stripped.split()

        # Camera format:
        # CAMERA_ID MODEL WIDTH HEIGHT PARAMS...
        if len(parts) >= 5 and parts[1] == "SIMPLE_PINHOLE":

            camera_id = parts[0]
            width = parts[2]
            height = parts[3]

            f_value = parts[4]
            cx = parts[5]
            cy = parts[6]

            # SIMPLE_PINHOLE:
            # f cx cy
            #
            # PINHOLE:
            # fx fy cx cy

            new_line = (
                f"{camera_id} PINHOLE "
                f"{width} {height} "
                f"{f_value} {f_value} {cx} {cy}\n"
            )

            new_camera_lines.append(new_line)

        else:
            new_camera_lines.append(line)


with open(cameras_txt, "w") as f:
    f.writelines(new_camera_lines)

print("\n✓ Đã chuyển SIMPLE_PINHOLE → PINHOLE")


# ==============================
# 3. SỬA TÊN ẢNH TRONG images.txt
# ==============================

new_image_lines = []
rename_count = 0

with open(images_txt, "r") as f:
    for line in f:

        # Trong images.txt, dòng thông tin camera/image
        # chứa tên file .jpg
        if ".jpg" in line or ".jpeg" in line or ".png" in line:

            old_line = line

            # frame_00000.jpg -> 00000.jpg
            line = re.sub(
                r'frame_(\d+\.(?:jpg|jpeg|png))',
                r'\1',
                line
            )

            if line != old_line:
                rename_count += 1

        new_image_lines.append(line)


with open(images_txt, "w") as f:
    f.writelines(new_image_lines)

print(f"✓ Đã sửa {rename_count} tên ảnh trong images.txt")


# ==============================
# 4. KIỂM TRA CAMERAS.TXT
# ==============================

print("\n========== CAMERA MODEL ==========")

models = set()

with open(cameras_txt, "r") as f:
    for line in f:

        if line.strip() and not line.startswith("#"):
            parts = line.split()

            if len(parts) >= 2:
                models.add(parts[1])

print("Camera models:", models)

if models == {"PINHOLE"}:
    print("✓ CAMERA MODEL OK: PINHOLE")
else:
    print("⚠ Vẫn còn camera model khác:", models)


# ==============================
# 5. KIỂM TRA TÊN ẢNH
# ==============================

print("\n========== KIỂM TRA ẢNH ==========")

actual_images = sorted([
    x for x in os.listdir(images_dir)
    if x.lower().endswith((".jpg", ".jpeg", ".png"))
])

print("Số ảnh trong images/:", len(actual_images))

print("\n10 ảnh đầu:")
for x in actual_images[:10]:
    print(" ", x)


# ==============================
# 6. KIỂM TRA images.txt
# ==============================

colmap_names = []

with open(images_txt, "r") as f:
    for line in f:

        if line.strip() and not line.startswith("#"):
            parts = line.split()

            # Dòng image metadata thường có >= 10 trường
            if len(parts) >= 10:
                name = parts[9]

                if name.lower().endswith((".jpg", ".jpeg", ".png")):
                    colmap_names.append(name)

print("\nSố ảnh COLMAP:", len(colmap_names))

print("\n10 tên ảnh COLMAP đầu:")
for x in colmap_names[:10]:
    print(" ", x)


# ==============================
# 7. KIỂM TRA KHỚP TÊN
# ==============================

actual_set = set(actual_images)
colmap_set = set(colmap_names)

missing_from_folder = colmap_set - actual_set
missing_from_colmap = actual_set - colmap_set

print("\n========== KẾT QUẢ ==========")

print("COLMAP nhưng không có trong images/:",
      len(missing_from_folder))

print("Có trong images/ nhưng không có COLMAP:",
      len(missing_from_colmap))

if len(missing_from_folder) == 0 and len(missing_from_colmap) == 0:
    print("\n🎉 DATASET KHỚP HOÀN TOÀN!")
else:
    print("\n⚠ Tên ảnh vẫn chưa khớp.")

    if missing_from_folder:
        print("\nMột số file COLMAP không tìm thấy:")
        for x in list(missing_from_folder)[:10]:
            print(" ", x)

    if missing_from_colmap:
        print("\nMột số ảnh không có trong COLMAP:")
        for x in list(missing_from_colmap)[:10]:
            print(" ", x)