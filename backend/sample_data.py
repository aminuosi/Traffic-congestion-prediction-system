from copy import deepcopy


PRESET_ROUTE = {
    "id": "preset-route",
    "name": "长深高速东庐山服务区示范路段",
    "direction": "上游至下游",
    "mode": "preset",
    "points": [
        {
            "id": "p1",
            "name": "观测点 1",
            "videoName": "1_1_20240501_20240501114103_20240501135755_114103.mp4",
            "fileUrl": "/media/preset/1_1_20240501_20240501114103_20240501135755_114103.mp4",
            "startTime": "11:41:03",
            "distanceFromPreviousKm": 0,
            "flow": 3.6,
            "density": 72.4,
            "avgSpeed": 58.6,
            "tpi": 21.16,
            "status": "轻微拥堵",
        },
        {
            "id": "p2",
            "name": "观测点 2",
            "videoName": "2_1_20240501_20240501115227_20240501130415_115227.mp4",
            "fileUrl": "/media/preset/2_1_20240501_20240501115227_20240501130415_115227.mp4",
            "startTime": "11:52:27",
            "distanceFromPreviousKm": 1.2,
            "flow": 2.8,
            "density": 61.8,
            "avgSpeed": 64.2,
            "tpi": 9.34,
            "status": "基本畅通",
        },
        {
            "id": "p3",
            "name": "观测点 3",
            "videoName": "3_1_20240501_20240501113543_20240501135236_113542.mp4",
            "fileUrl": "/media/preset/3_1_20240501_20240501113543_20240501135236_113542.mp4",
            "startTime": "11:35:43",
            "distanceFromPreviousKm": 1.85,
            "flow": 4.1,
            "density": 84.7,
            "avgSpeed": 42.5,
            "tpi": 45.43,
            "status": "拥堵抬升",
        },
        {
            "id": "p4",
            "name": "观测点 4",
            "videoName": "4_1_20240501_20240501125647_20240501140806_125649.mp4",
            "fileUrl": "/media/preset/4_1_20240501_20240501125647_20240501140806_125649.mp4",
            "startTime": "12:56:47",
            "distanceFromPreviousKm": 1.6,
            "flow": 4.5,
            "density": 91.3,
            "avgSpeed": 35.9,
            "tpi": 84.04,
            "status": "严重拥堵",
        },
    ],
}


def calculate_distances(points):
    total = 0.0
    enriched = []
    for index, point in enumerate(points):
        next_point = dict(point)
        if index > 0:
            total += float(next_point.get("distanceFromPreviousKm", 0) or 0)
        next_point["distanceFromStartKm"] = round(total, 2)
        enriched.append(next_point)
    return enriched


def get_preset_route():
    route = deepcopy(PRESET_ROUTE)
    route["points"] = calculate_distances(route["points"])
    route["totalLengthKm"] = route["points"][-1]["distanceFromStartKm"]
    return route
