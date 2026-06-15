from pathlib import Path
from urllib.parse import quote


def resolve_media_path(root, upload_dir, relative):
    if relative.startswith("preset/"):
        filename = relative[len("preset/") :]
        search_paths = [
            root.parent / "代码" / filename,
            root.parent / "代码" / "code" / filename,
        ]
        target = next((candidate for candidate in search_paths if candidate.exists()), None)
        if target is None:
            stem = Path(filename).stem
            for preset_dir in [root.parent / "代码", root.parent / "代码" / "code"]:
                matches = sorted(preset_dir.glob(f"{stem}*.mp4")) if preset_dir.exists() else []
                if matches:
                    target = matches[0]
                    break
        return target

    if relative.startswith("uploads/"):
        filename = relative[len("uploads/") :]
        return upload_dir / Path(filename).name

    return None


def mjpeg_frames(video_path, max_width=960, preview_stride=3):
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
      return

    frame_index = 0
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
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buffer.tobytes()
                    + b"\r\n"
                )
            frame_index += 1
    finally:
        cap.release()


def preview_url(media_url):
    if not media_url.startswith("/media/"):
        return media_url
    return "/preview/" + quote(media_url[len("/media/") :])
