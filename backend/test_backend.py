from analyzer import (
    analyze_video_full,
    build_prediction_summary,
    calculate_tpi,
    dependency_status,
    extract_real_time_from_filename,
    summarize_route,
)
from lane_decision import build_lane_decision
from sample_data import get_preset_route
from video_preview import resolve_media_path


def test_preset_route():
    route = get_preset_route()
    assert route["name"] == "长深高速东庐山服务区示范路段"
    assert len(route["points"]) == 4
    assert route["points"][3]["distanceFromStartKm"] == 4.65


def test_prediction_summary():
    route = get_preset_route()
    summary = build_prediction_summary(route)
    assert summary["status"] == "建议开启应急车道"
    assert summary["laneDecision"]["mode"] == "open_lane"
    assert summary["warningTime"] == "13:28:07"
    assert summary["keySegment"] == "观测点 3 至 观测点 4"


def test_summarize_route_recalculates_distances():
    route = {
        "points": [
            {"name": "A", "distanceFromPreviousKm": 0},
            {"name": "B", "distanceFromPreviousKm": 1.4},
            {"name": "C", "distanceFromPreviousKm": 2.2},
        ]
    }
    summarized = summarize_route(route)
    assert summarized["totalLengthKm"] == 3.6
    assert [point["distanceFromStartKm"] for point in summarized["points"]] == [0, 1.4, 3.6]


def test_dependency_status_reports_missing_yolo_stack():
    status = dependency_status()
    assert "ready" in status
    assert "missing" in status


def test_extract_real_time_from_filename():
    result = extract_real_time_from_filename("4_1_20240501_20240501125647_20240501140806_125649.mp4")
    assert result["startTime"] == "12:56:47"
    assert result["endTime"] == "14:08:06"
    assert result["durationSeconds"] == 4279


def test_low_flow_low_density_does_not_produce_severe_tpi():
    assert calculate_tpi(flow=0.04, density=2.0, avg_speed=55.0) < 25


def test_preset_preview_falls_back_to_uploads_when_project_is_moved(tmp_path):
    root = tmp_path / "web-system"
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True)
    target = upload_dir / "1_1_20240501_20240501114103_20240501135755_114103.mp4"
    target.write_bytes(b"fake mp4")

    resolved = resolve_media_path(
        root,
        upload_dir,
        "preset/1_1_20240501_20240501114103_20240501135755_114103.mp4",
    )

    assert resolved == target


def test_lane_decision_holds_when_tpi_is_low():
    decision = build_lane_decision({"points": [{"tpi": 8}, {"tpi": 10}, {"tpi": 12}]})
    assert decision["decision"] == "暂不开启"


def test_analyze_video_full_does_not_fake_results_when_dependencies_missing():
    status = dependency_status()
    if status["ready"]:
        return
    result = analyze_video_full("missing.mp4")
    assert result["ok"] is False
    assert "依赖缺失" in result["status"]


if __name__ == "__main__":
    test_preset_route()
    test_prediction_summary()
    test_summarize_route_recalculates_distances()
    test_dependency_status_reports_missing_yolo_stack()
    test_extract_real_time_from_filename()
    test_low_flow_low_density_does_not_produce_severe_tpi()
    from tempfile import TemporaryDirectory
    from pathlib import Path
    with TemporaryDirectory() as directory:
        test_preset_preview_falls_back_to_uploads_when_project_is_moved(Path(directory))
    test_lane_decision_holds_when_tpi_is_low()
    test_analyze_video_full_does_not_fake_results_when_dependencies_missing()
    print("backend tests passed")
