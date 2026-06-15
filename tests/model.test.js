import test from "node:test";
import assert from "node:assert/strict";

import {
  createPresetRoute,
  movePoint,
  updateSegmentDistance,
  calculateDistanceFromStart,
  createPredictionSummary,
} from "../src/model.js";

test("createPresetRoute returns ordered thesis monitoring points", () => {
  const route = createPresetRoute();

  assert.equal(route.name, "长深高速东庐山服务区示范路段");
  assert.equal(route.points.length, 4);
  assert.deepEqual(route.points.map((point) => point.name), [
    "观测点 1",
    "观测点 2",
    "观测点 3",
    "观测点 4",
  ]);
  assert.equal(route.points[0].videoName.includes("114103"), true);
});

test("movePoint reorders monitoring points without mutating source route", () => {
  const route = createPresetRoute();
  const moved = movePoint(route, "p4", "p2");

  assert.deepEqual(moved.points.map((point) => point.id), ["p1", "p4", "p2", "p3"]);
  assert.deepEqual(route.points.map((point) => point.id), ["p1", "p2", "p3", "p4"]);
});

test("updateSegmentDistance recalculates distance from route start", () => {
  const route = createPresetRoute();
  const updated = updateSegmentDistance(route, "p3", 2.25);
  const distances = calculateDistanceFromStart(updated.points);

  assert.deepEqual(distances.map((value) => Number(value.toFixed(2))), [0, 1.2, 3.45, 5.05]);
  assert.equal(updated.points[2].distanceFromPreviousKm, 2.25);
});

test("createPredictionSummary reports congestion window and lane decision", () => {
  const route = createPresetRoute();
  const summary = createPredictionSummary(route);

  assert.equal(summary.status, "建议开启应急车道");
  assert.equal(summary.warningTime, "13:28:07");
  assert.equal(summary.congestionWindow, "13:38:07 - 14:22:27");
  assert.equal(summary.keySegment, "观测点 3 至 观测点 4");
  assert.equal(summary.modelScores[0].model, "LSTM");
});
