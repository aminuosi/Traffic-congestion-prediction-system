import {
  appendUploadedFiles,
  createEmptyRoute,
  createPredictionSummary,
  createPresetRoute,
  movePoint,
  updateSegmentDistance,
} from "./model.js";

let route = createPresetRoute();
let selectedPointId = route.points[0]?.id ?? null;
let draggedPointId = null;
const API_BASE = "http://127.0.0.1:8099";

const pointList = document.querySelector("#pointList");
const distanceInputs = document.querySelector("#distanceInputs");
const routeNameInput = document.querySelector("#routeNameInput");
const routeDirectionInput = document.querySelector("#routeDirectionInput");
const videoUpload = document.querySelector("#videoUpload");
const videoFrame = document.querySelector("#videoFrame");
const selectedVideoFile = document.querySelector("#selectedVideoFile");
const selectedPointName = document.querySelector("#selectedPointName");
const selectedPointFile = document.querySelector("#selectedPointFile");
const flowValue = document.querySelector("#flowValue");
const densityValue = document.querySelector("#densityValue");
const speedValue = document.querySelector("#speedValue");
const tpiValue = document.querySelector("#tpiValue");
const statusValue = document.querySelector("#statusValue");
const tpiBars = document.querySelector("#tpiBars");
const decisionCard = document.querySelector("#decisionCard");

document.querySelector("#loadPresetBtn").addEventListener("click", async () => {
  route = await loadPresetRoute();
  selectedPointId = route.points[0]?.id ?? null;
  render();
});

document.querySelector("#emptyRouteBtn").addEventListener("click", () => {
  route = createEmptyRoute();
  selectedPointId = null;
  render();
});

document.querySelector("#predictBtn").addEventListener("click", async () => {
  renderDecision(await requestPrediction(route));
});

routeNameInput.addEventListener("input", (event) => {
  route = { ...route, name: event.target.value };
});

routeDirectionInput.addEventListener("input", (event) => {
  route = { ...route, direction: event.target.value };
});

videoUpload.addEventListener("change", async (event) => {
  route = await uploadVideos(route, event.target.files);
  selectedPointId = route.points.at(-1)?.id ?? selectedPointId;
  videoUpload.value = "";
  render();
});

async function loadPresetRoute() {
  try {
    const response = await fetch(`${API_BASE}/api/preset-route`);
    if (!response.ok) {
      throw new Error("preset route request failed");
    }
    return await response.json();
  } catch (error) {
    return createPresetRoute();
  }
}

async function requestPrediction(currentRoute) {
  try {
    const response = await fetch(`${API_BASE}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ route: currentRoute }),
    });
    if (!response.ok) {
      throw new Error("prediction request failed");
    }
    return await response.json();
  } catch (error) {
    return createPredictionSummary(currentRoute);
  }
}

async function uploadVideos(currentRoute, files) {
  const fileList = Array.from(files);
  if (fileList.length === 0) {
    return currentRoute;
  }

  try {
    const body = new FormData();
    fileList.forEach((file) => body.append("files", file));
    const response = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body,
    });
    if (!response.ok) {
      throw new Error("upload request failed");
    }
    const payload = await response.json();
    const analyzedPoints = await analyzeUploadedVideos(payload.points);
    return {
      ...currentRoute,
      mode: "upload",
      points: [...currentRoute.points, ...analyzedPoints].map((point, index, all) => {
        const distanceFromStartKm = all
          .slice(0, index + 1)
          .reduce((total, item, itemIndex) => {
            if (itemIndex === 0) return 0;
            return total + Number(item.distanceFromPreviousKm || 0);
          }, 0);
        return { ...point, distanceFromStartKm: Number(distanceFromStartKm.toFixed(2)) };
      }),
    };
  } catch (error) {
    return appendUploadedFiles(currentRoute, fileList);
  }
}

async function analyzeUploadedVideos(points) {
  const analyzed = [];
  for (const [index, point] of points.entries()) {
    try {
      const response = await fetch(`${API_BASE}/api/analyze-video`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: point.videoName, index }),
      });
      if (!response.ok) {
        throw new Error("analysis request failed");
      }
      const result = await response.json();
      if (result.ok && result.point) {
        analyzed.push(result.point);
      } else {
        analyzed.push({
          ...point,
          status: result.status || "真实分析未执行",
          analysisMessage: result.message || (result.missing ? `缺少依赖：${result.missing.join(", ")}` : ""),
        });
      }
    } catch (error) {
      analyzed.push({
        ...point,
        status: "真实分析请求失败",
        analysisMessage: "后端分析接口暂不可用，当前仅保存视频。",
      });
    }
  }
  return analyzed;
}

function getSelectedPoint() {
  return route.points.find((point) => point.id === selectedPointId) ?? route.points[0] ?? null;
}

function render() {
  routeNameInput.value = route.name;
  routeDirectionInput.value = route.direction;
  renderPoints();
  renderDistances();
  renderSelectedPoint();
  renderTpiBars();
  renderDecisionPlaceholder();
}

function renderPoints() {
  pointList.innerHTML = "";

  if (route.points.length === 0) {
    pointList.innerHTML = '<div class="video-placeholder">上传视频后，可拖拽到路段上排序</div>';
    return;
  }

  route.points.forEach((point, index) => {
    const card = document.createElement("article");
    card.className = `point-card${point.id === selectedPointId ? " selected" : ""}`;
    card.draggable = true;
    card.dataset.id = point.id;
    card.innerHTML = `
      <div class="camera-dot">${index + 1}</div>
      <div class="point-name">${point.name}</div>
      <div class="point-file">${point.videoName}</div>
      <div class="point-stat"><span>距起点</span><strong>${point.distanceFromStartKm ?? 0} km</strong></div>
      <div class="point-stat"><span>开始时间</span><strong>${point.startTime}</strong></div>
      <div class="point-stat"><span>状态</span><strong>${point.status}</strong></div>
    `;

    card.addEventListener("click", () => {
      selectedPointId = point.id;
      render();
    });

    card.addEventListener("dragstart", () => {
      draggedPointId = point.id;
      card.classList.add("selected");
    });

    card.addEventListener("dragover", (event) => {
      event.preventDefault();
      card.classList.add("drag-over");
    });

    card.addEventListener("dragleave", () => {
      card.classList.remove("drag-over");
    });

    card.addEventListener("drop", (event) => {
      event.preventDefault();
      card.classList.remove("drag-over");
      route = movePoint(route, draggedPointId, point.id);
      selectedPointId = draggedPointId;
      draggedPointId = null;
      render();
    });

    pointList.appendChild(card);
  });
}

function renderDistances() {
  distanceInputs.innerHTML = "";

  if (route.points.length < 2) {
    distanceInputs.innerHTML = '<p class="muted">至少需要两个视频点位才能设置相邻距离。</p>';
    return;
  }

  route.points.slice(1).forEach((point, index) => {
    const previous = route.points[index];
    const label = document.createElement("label");
    label.innerHTML = `
      ${previous.name} 至 ${point.name}
      <input type="number" min="0" step="0.05" value="${point.distanceFromPreviousKm}" data-id="${point.id}" />
    `;
    label.querySelector("input").addEventListener("input", (event) => {
      route = updateSegmentDistance(route, point.id, event.target.value);
      renderPoints();
      renderTpiBars();
    });
    distanceInputs.appendChild(label);
  });
}

function renderSelectedPoint() {
  const point = getSelectedPoint();

  if (!point) {
    selectedPointName.textContent = "未选择点位";
    selectedVideoFile.textContent = "请在左侧上传或选择视频卡片";
    selectedPointFile.textContent = "点位信息";
    videoFrame.innerHTML = '<div class="video-placeholder">暂无视频</div>';
    setMetric("--", "--", "--", "--", "待分析");
    return;
  }

  selectedPointName.textContent = point.name;
  selectedVideoFile.textContent = point.videoName;
  selectedPointFile.textContent = `开始时间 ${point.startTime} · 距起点 ${point.distanceFromStartKm ?? 0} km`;
  setMetric(point.flow, point.density, point.avgSpeed, point.tpi, point.status);

  if (point.fileUrl) {
    const src = point.fileUrl.startsWith("/media/")
      ? `${API_BASE}${point.fileUrl}`
      : point.fileUrl;
    const previewSrc = point.fileUrl.startsWith("/media/")
      ? `${API_BASE}/preview/${encodeURIComponent(point.fileUrl.replace("/media/", ""))}`
      : point.fileUrl;
    videoFrame.innerHTML = `
      <img class="video-preview-stream" src="${previewSrc}" alt="${point.videoName} 预览画面" />
      <div class="video-actions">
        <a href="${src}" target="_blank" rel="noreferrer">在新标签打开视频</a>
        <span>当前使用后端帧流预览，可绕开原视频编码兼容问题。</span>
      </div>
    `;
  } else {
    videoFrame.innerHTML = `
      <div class="video-placeholder">
        <div>
          <strong>预置视频点位</strong><br />
          ${point.videoName}<br />
          <span>接入真实视频后，此处播放原始/检测结果视频</span>
        </div>
      </div>
    `;
  }

  if (point.analysisMessage) {
    const note = document.createElement("p");
    note.className = "analysis-note";
    note.textContent = point.analysisMessage;
    videoFrame.insertAdjacentElement("afterend", note);
  }
}

function setMetric(flow, density, speed, tpi, status) {
  flowValue.textContent = formatMetric(flow);
  densityValue.textContent = formatMetric(density);
  speedValue.textContent = formatMetric(speed);
  tpiValue.textContent = formatMetric(tpi);
  statusValue.textContent = status;
}

function formatMetric(value) {
  if (value === "--" || value === undefined || value === null) {
    return "--";
  }
  return Number(value).toFixed(2);
}

function renderTpiBars() {
  tpiBars.innerHTML = "";

  if (route.points.length === 0) {
    tpiBars.innerHTML = '<p class="muted">暂无 TPI 数据。</p>';
    return;
  }

  const maxTpi = Math.max(...route.points.map((point) => point.tpi || 0), 1);
  route.points.forEach((point) => {
    const row = document.createElement("div");
    row.className = "tpi-row";
    const percent = Math.max(6, Math.min(100, ((point.tpi || 0) / maxTpi) * 100));
    row.innerHTML = `
      <span>${point.name}</span>
      <div class="bar-track"><div class="bar-fill" style="width: ${percent}%"></div></div>
      <strong>${formatMetric(point.tpi)}</strong>
    `;
    tpiBars.appendChild(row);
  });
}

function renderDecisionPlaceholder() {
  decisionCard.innerHTML = `
    <div class="section-title">预测与决策输出</div>
    <p class="muted">完成路段排布后点击“开始预测”。系统会根据距离、时间和多点 TPI 趋势输出拥堵区间与应急车道建议。</p>
  `;
}

function renderDecision(summary) {
  decisionCard.innerHTML = `
    <div class="section-title">预测与决策输出</div>
    <div class="decision-status">${summary.status}</div>
    <div class="decision-grid">
      <div class="decision-item"><span>预警时间</span><strong>${summary.warningTime}</strong></div>
      <div class="decision-item"><span>拥堵区间</span><strong>${summary.congestionWindow}</strong></div>
      <div class="decision-item"><span>重点路段</span><strong>${summary.keySegment}</strong></div>
    </div>
    <p>${summary.reason}</p>
    <div class="model-list">
      ${summary.modelScores
        .map(
          (score) => `
            <div class="model-row">
              <strong>${score.model}</strong>
              <span>MSE ${score.mse} · ${score.note}</span>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

render();
