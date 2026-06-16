from pathlib import Path
import re
import time
from urllib.parse import quote


def resolve_media_path(root, upload_dir, relative):
    if relative.startswith("preset/"):
        filename = relative[len("preset/") :]
        search_dirs = [
            root / "preset-videos",
            root / "uploads",
            root / "media" / "preset",
            root.parent / "代码",
            root.parent / "代码" / "code",
            root.parent / "代码" / "高速公路交通流数据",
        ]
        return find_video_file(filename, search_dirs)

    if relative.startswith("uploads/"):
        filename = relative[len("uploads/") :]
        return upload_dir / Path(filename).name

    return None


def find_video_file(filename, search_dirs):
    safe_name = Path(filename).name
    exact_matches = [directory / safe_name for directory in search_dirs]
    target = next((candidate for candidate in exact_matches if candidate.exists()), None)
    if target is not None:
        return target

    stem = Path(safe_name).stem
    for directory in search_dirs:
        if not directory.exists():
            continue
        matches = sorted(directory.rglob(f"{stem}*.mp4"))
        if matches:
            return matches[0]

    timestamps = re.findall(r"20\d{12}", safe_name)
    if timestamps:
        for directory in search_dirs:
            if not directory.exists():
                continue
            for candidate in sorted(directory.rglob("*.mp4")):
                if all(timestamp in candidate.name for timestamp in timestamps):
                    return candidate

    return None


def mjpeg_frames(video_path, max_width=960, preview_stride=3, preview_fps=10, loop=True):
    import cv2

    delay = 1 / max(preview_fps, 1)

    while True:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return

        frame_index = 0
        emitted = False
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_index % preview_stride != 0:
                    frame_index += 1
                    continue
                height, width = frame.shape[:2]
                if width > max_width:
                    new_height = int(height * (max_width / width))
                    frame = cv2.resize(frame, (max_width, new_height))
                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
                if ok:
                    emitted = True
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + buffer.tobytes()
                        + b"\r\n"
                    )
                    time.sleep(delay)
                frame_index += 1
        finally:
            cap.release()

        if not loop or not emitted:
            break


def preview_url(media_url):
    if not media_url.startswith("/media/"):
        return media_url
    return "/preview/" + quote(media_url[len("/media/") :])
