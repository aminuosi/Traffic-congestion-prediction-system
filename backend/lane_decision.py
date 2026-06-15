def build_lane_decision(summary):
    points = summary.get("points", [])
    if not points:
        return {
            "decision": "不建议开启",
            "reason": "缺少有效 TPI 数据，暂无法进行应急车道判断。",
            "threshold": 25,
            "windowMinutes": 30,
            "mode": "insufficient_data",
        }

    future_tpi = [point.get("tpi", 0) for point in points]
    max_tpi = max(future_tpi)
    avg_tpi = sum(future_tpi) / len(future_tpi)
    rising = future_tpi[-1] >= future_tpi[0] if len(future_tpi) >= 2 else False

    if max_tpi >= 50 and avg_tpi >= 28 and rising:
        decision = "建议开启应急车道"
        reason = "未来 30 分钟内 TPI 持续高于拥堵阈值且呈上升趋势，满足提前启用条件。"
        mode = "open_lane"
    elif max_tpi >= 25 and rising:
        decision = "预警观察"
        reason = "拥堵指数有上升趋势，但尚未持续达到严重拥堵阈值。"
        mode = "warning"
    else:
        decision = "暂不开启"
        reason = "TPI 整体未持续超阈值，暂不满足开启应急车道条件。"
        mode = "hold"

    return {
        "decision": decision,
        "reason": reason,
        "threshold": 25,
        "windowMinutes": 30,
        "maxTpi": round(max_tpi, 2),
        "avgTpi": round(avg_tpi, 2),
        "mode": mode,
    }
