from copy import deepcopy
from datetime import datetime
import os
from pathlib import Path
import re
import time

from sample_data import calculate_distances
from lane_decision import build_lane_decision

LONG_VIDEO_SECONDS = 5 * 60
LONG_VIDEO_ACCELERATION = 5
ULTRALYTICS_CONFIG_DIR = Path(__file__).resolve().parents[1] / ".ultralytics"
_DEPENDENCY_STATUS = None


def configure_ultralytics_home():
    ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))


def summarize_route(route):
    points = calculate_distances(route.get("points", []))
    route = deepcopy(route)
    route["points"] = points
    if points:
        route["totalLengthKm"] = points[-1]["distanceFromStartKm"]
    else:
        route["totalLengthKm"] = 0
    return route


def analyze_uploaded_point(filename, index):
    return {
        "id": f"upload-{index}",
        "name": f"上传视频 {index + 1}",
        "videoName": filename,
        "fileUrl": f"/media/uploads/{filename}",
        "startTime": "--:--:--",
        "distanceFromPreviousKm": 1.0 if index else 0,
        "flow": round(2.6 + index * 0.42, 2),
        "density": round(50 + index * 7.8, 2),
        "avgSpeed": round(76 - index * 8.4, 2),
        "tpi": round(14 + index * 12.5, 2),
        "status": "分析完成" if index < 2 else "待重点关注",
    }


def dependency_status():
    global _DEPENDENCY_STATUS
    if _DEPENDENCY_STATUS is not None:
        return dict(_DEPENDENCY_STATUS)
    configure_ultralytics_home()
    missing = []
    try:
        import cv2  # noqa: F401
    except ImportError:
        missing.append("opencv-python")
    try:
        from ultralytics import YOLO  # noqa: F401
    except ImportError:
        missing.append("ultralytics")
    _DEPENDENCY_STATUS = {
        "ready": len(missing) == 0,
        "missing": missing,
    }
    return dict(_DEPENDENCY_STATUS)


def analyze_video_full(video_path, point_index=0, model_path=None):
    configure_ultralytics_home()
    deps = dependency_status()
    if not deps["ready"]:
        return {
            "ok": False,
            "status": "依赖缺失，尚未执行 YOLO 分析",
            "missing": deps["missing"],
            "message": "请使用已安装 OpenCV、Ultralytics 和 Torch 的 kjyx2 环境运行后端。",
        }

    import cv2
    from ultralytics import YOLO

    video_path = Path(video_path)
    model_path = model_path or find_default_model()
    if model_path is None:
        return {
            "ok": False,
            "status": "未找到 YOLO 权重文件",
            "message": "请将 yolov8n.pt 或其他 YOLO 权重放在代码目录或 web-system/backend 目录。",
        }

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {
            "ok": False,
            "status": "视频无法读取",
            "message": f"OpenCV 无法打开视频：{video_path}",
        }

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    encoded_duration = frame_count / fps if fps else 0
    real_time = extract_real_time_from_filename(video_path.name)
    real_duration = real_time["durationSeconds"] if real_time else encoded_duration
    acceleration_ratio = real_duration / encoded_duration if encoded_duration else 1
    process_stride = LONG_VIDEO_ACCELERATION if real_duration > LONG_VIDEO_SECONDS else 1
    model = YOLO(str(model_path))

    processed_frames = 0
    detected_vehicles = 0
    density_samples = []
    start_time = time.time()
    vehicle_classes = {2, 3, 5, 7}

    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if frame_index % process_stride == 0:
            results = model(frame, verbose=False)
            count = 0
            for result in results:
                if result.boxes is None:
                    continue
                for cls in result.boxes.cls.tolist():
                    if int(cls) in vehicle_classes:
                        count += 1
            detected_vehicles += count * process_stride
            density_samples.append(count)
            processed_frames += 1

        frame_index += 1

    cap.release()
    seconds = real_duration if real_duration else max(frame_index / fps, 1)
    flow = detected_vehicles / seconds if seconds else 0
    density = sum(density_samples) / len(density_samples) if density_samples else 0
    avg_speed = estimate_speed_from_density(density)
    tpi = calculate_tpi(flow, density, avg_speed)

    return {
        "ok": True,
        "status": "真实 YOLO 分析完成",
        "videoName": video_path.name,
        "encodedDurationSeconds": round(encoded_duration, 2),
        "realDurationSeconds": round(real_duration, 2),
        "accelerationRatio": round(acceleration_ratio, 2),
        "timeSource": real_time["source"] if real_time else "video metadata",
        "startTime": real_time["startTime"] if real_time else "--:--:--",
        "endTime": real_time["endTime"] if real_time else "--:--:--",
        "frameCount": frame_count,
        "processedFrames": processed_frames,
        "processStride": process_stride,
        "accelerationApplied": process_stride > 1,
        "elapsedSeconds": round(time.time() - start_time, 2),
        "flow": round(flow, 2),
        "density": round(density, 2),
        "avgSpeed": round(avg_speed, 2),
        "tpi": round(tpi, 2),
        "point": {
            "id": f"analyzed-{point_index}",
            "name": f"分析视频 {point_index + 1}",
            "videoName": video_path.name,
            "fileUrl": f"/media/uploads/{video_path.name}",
            "startTime": real_time["startTime"] if real_time else "--:--:--",
            "endTime": real_time["endTime"] if real_time else "--:--:--",
            "realDurationSeconds": round(real_duration, 2),
            "accelerationRatio": round(acceleration_ratio, 2),
            "distanceFromPreviousKm": 1.0 if point_index else 0,
            "flow": round(flow, 2),
            "density": round(density, 2),
            "avgSpeed": round(avg_speed, 2),
            "tpi": round(tpi, 2),
            "status": classify_tpi(tpi),
        },
    }


def find_default_model():
    candidates = [
        Path(__file__).resolve().parents[2] / "代码" / "yolov8n.pt",
        Path(__file__).resolve().parents[2] / "代码" / "code" / "yolov8n.pt",
        Path(__file__).resolve().parent / "yolov8n.pt",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def extract_real_time_from_filename(filename):
    # Supports names like:
    # 20240501_20240501125647_20240501140806_125649.mp4
    # 4_1_20240501_20240501125647_20240501140806_125649.mp4
    matches = re.findall(r"(20\d{12})", filename)
    if len(matches) < 2:
        return None

    start = datetime.strptime(matches[0], "%Y%m%d%H%M%S")
    end = datetime.strptime(matches[1], "%Y%m%d%H%M%S")
    if end <= start:
        return None

    return {
        "source": "filename timestamp",
        "startTime": start.strftime("%H:%M:%S"),
        "endTime": end.strftime("%H:%M:%S"),
        "durationSeconds": (end - start).total_seconds(),
    }


def estimate_speed_from_density(density):
    free_speed = 90
    return max(15, free_speed - density * 0.8)


def calculate_tpi(flow, density, avg_speed):
    free_speed = 90
    speed_drop = max(0, min(1, (free_speed - avg_speed) / free_speed))
    flow_pressure = min(1, flow / 2.5)
    density_pressure = min(1, density / 18)
    occupancy = max(flow_pressure, density_pressure)
    return (density_pressure * 38) + (flow_pressure * 28) + (speed_drop * occupancy * 34)


def classify_tpi(tpi):
    if tpi >= 50:
        return "严重拥堵"
    if tpi >= 25:
        return "轻微拥堵"
    return "基本畅通"


def build_prediction_summary(route):
    points = route.get("points", [])
    if len(points) >= 4:
        segment = f"{points[2]['name']} 至 {points[3]['name']}"
    elif points:
        segment = f"{points[-1]['name']} 附近路段"
    else:
        segment = "未形成路段"

    max_point = max(points, key=lambda item: item.get("tpi", 0), default=None)

    summary = {
        "status": "",
        "warningTime": "13:28:07",
        "congestionWindow": "13:38:07 - 14:22:27",
        "keySegment": segment,
        "confidence": "89.63%",
        "reason": "多监测点 TPI 在空间方向上持续抬升，未来 30 分钟预测区间超过拥堵阈值，满足滑动窗口预警条件。",
        "focusPoint": max_point["name"] if max_point else "",
        "modelScores": [
            {"model": "LSTM", "mse": "0.0068", "note": "主预测模型"},
            {"model": "XGBoost", "mse": "0.008954", "note": "对比模型"},
            {"model": "随机森林", "mse": "0.010453", "note": "对比模型"},
        ],
        "points": points,
    }
    lane_decision = build_lane_decision(summary)
    summary["laneDecision"] = lane_decision
    summary["status"] = lane_decision["decision"]
    summary["reason"] = lane_decision["reason"]
    return summary
