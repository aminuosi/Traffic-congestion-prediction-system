const presetPoints = [
  {
    id: "p1",
    name: "观测点 1",
    videoName: "1_1_20240501_20240501114103_20240501135755_114103.mp4",
    fileUrl: "/media/preset/1_1_20240501_20240501114103_20240501135755_114103.mp4",
    startTime: "11:41:03",
    distanceFromPreviousKm: 0,
    flow: 3.6,
    density: 72.4,
    avgSpeed: 58.6,
    tpi: 21.16,
    status: "轻微拥堵",
  },
  {
    id: "p2",
    name: "观测点 2",
    videoName: "2_1_20240501_20240501115227_20240501130415_115227.mp4",
    fileUrl: "/media/preset/2_1_20240501_20240501115227_20240501130415_115227.mp4",
    startTime: "11:52:27",
    distanceFromPreviousKm: 1.2,
    flow: 2.8,
    density: 61.8,
    avgSpeed: 64.2,
    tpi: 9.34,
    status: "基本畅通",
  },
  {
    id: "p3",
    name: "观测点 3",
    videoName: "3_1_20240501_20240501113543_20240501135236_113542.mp4",
    fileUrl: "/media/preset/3_1_20240501_20240501113543_20240501135236_113542.mp4",
    startTime: "11:35:43",
    distanceFromPreviousKm: 1.85,
    flow: 4.1,
    density: 84.7,
    avgSpeed: 42.5,
    tpi: 45.43,
    status: "拥堵抬升",
  },
  {
    id: "p4",
    name: "观测点 4",
    videoName: "4_1_20240501_20240501125647_20240501140806_125649.mp4",
    fileUrl: "/media/preset/4_1_20240501_20240501125647_20240501140806_125649.mp4",
    startTime: "12:56:47",
    distanceFromPreviousKm: 1.6,
    flow: 4.5,
    density: 91.3,
    avgSpeed: 35.9,
    tpi: 84.04,
    status: "严重拥堵",
  },
];

export function calculateDistanceFromStart(points) {
  let total = 0;
  return points.map((point, index) => {
    if (index > 0) {
      total += Number(point.distanceFromPreviousKm || 0);
    }
    return total;
  });
}

function withDistances(points) {
  const distances = calculateDistanceFromStart(points);
  return points.map((point, index) => ({
    ...point,
    distanceFromStartKm: Number(distances[index].toFixed(2)),
  }));
}

export function createPresetRoute() {
  return {
    id: "preset-route",
    name: "长深高速东庐山服务区示范路段",
    direction: "上游至下游",
    totalLengthKm: 4.65,
    mode: "preset",
    points: withDistances(presetPoints),
  };
}

export function movePoint(route, draggedId, targetId) {
  if (draggedId === targetId) {
    return route;
  }

  const nextPoints = route.points.map((point) => ({ ...point }));
  const fromIndex = nextPoints.findIndex((point) => point.id === draggedId);
  const toIndex = nextPoints.findIndex((point) => point.id === targetId);

  if (fromIndex < 0 || toIndex < 0) {
    return route;
  }

  const [dragged] = nextPoints.splice(fromIndex, 1);
  nextPoints.splice(toIndex, 0, dragged);
  nextPoints[0].distanceFromPreviousKm = 0;

  return {
    ...route,
    points: withDistances(nextPoints),
  };
}

export function updateSegmentDistance(route, pointId, distanceKm) {
  const nextPoints = route.points.map((point) => {
    if (point.id !== pointId) {
      return { ...point };
    }
    return {
      ...point,
      distanceFromPreviousKm: Number(distanceKm),
    };
  });

  return {
    ...route,
    totalLengthKm: Number(calculateDistanceFromStart(nextPoints).at(-1).toFixed(2)),
    points: withDistances(nextPoints),
  };
}

export function createUploadedPoint(file, index) {
  return {
    id: `upload-${Date.now()}-${index}`,
    name: `上传视频 ${index + 1}`,
    videoName: file.name,
    fileUrl: createLocalPreviewUrl(file),
    startTime: "--:--:--",
    distanceFromPreviousKm: index === 0 ? 0 : 1,
    flow: Number((2.4 + index * 0.45).toFixed(2)),
    density: Number((48 + index * 8.5).toFixed(2)),
    avgSpeed: Number((78 - index * 9.2).toFixed(2)),
    tpi: Number((12 + index * 13.5).toFixed(2)),
    status: index > 1 ? "待重点关注" : "分析完成",
  };
}

function createLocalPreviewUrl(file) {
  if (typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
    try {
      return URL.createObjectURL(file);
    } catch (error) {
      return "";
    }
  }
  return "";
}

export function appendUploadingFiles(route, files) {
  const created = Array.from(files).map((file, index) =>
    withUploadState(createUploadedPoint(file, index), {
      analysisStatus: "uploading",
      analysisProgress: 8,
      analysisMessage: "文件已加入路段，正在上传并分析。",
    })
  );

  return {
    ...route,
    mode: "upload",
    points: withDistances([...route.points, ...created]),
  };
}

export function withUploadState(point, state) {
  return {
    ...point,
    analysisStatus: state.analysisStatus ?? point.analysisStatus ?? "ready",
    analysisProgress: state.analysisProgress ?? point.analysisProgress ?? 100,
    analysisMessage: state.analysisMessage ?? point.analysisMessage ?? "",
  };
}

export function hasPendingAnalysis(points) {
  return points.some((point) => ["uploading", "analyzing"].includes(point.analysisStatus));
}

export function appendUploadedFiles(route, files) {
  const created = Array.from(files).map((file, index) =>
    createUploadedPoint(file, route.points.length + index)
  );

  return {
    ...route,
    mode: "upload",
    points: withDistances([...route.points, ...created]),
  };
}

export function createEmptyRoute() {
  return {
    id: "custom-route",
    name: "自定义高速路段",
    direction: "上游至下游",
    totalLengthKm: 0,
    mode: "upload",
    points: [],
  };
}

export function createPredictionSummary(route) {
  const points = route.points;
  const highestTpiPoint = [...points].sort((a, b) => b.tpi - a.tpi)[0];
  const keySegment =
    points.length >= 4
      ? `${points[2].name} 至 ${points[3].name}`
      : highestTpiPoint
        ? `${highestTpiPoint.name} 附近路段`
        : "未形成路段";

  return {
    status: "建议开启应急车道",
    warningTime: "13:28:07",
    congestionWindow: "13:38:07 - 14:22:27",
    keySegment,
    confidence: "89.63%",
    reason:
      "多监测点 TPI 在空间方向上持续抬升，未来 30 分钟预测区间超过拥堵阈值，满足滑动窗口预警条件。",
    modelScores: [
      { model: "LSTM", mse: "0.0068", note: "主预测模型" },
      { model: "XGBoost", mse: "0.008954", note: "对比模型" },
      { model: "随机森林", mse: "0.010453", note: "对比模型" },
    ],
  };
}
