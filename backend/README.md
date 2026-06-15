# 智行枢纽后端服务

这是 Web 原型的 Python 后端。真实 YOLOv8 分析需要使用已配置 `cv2`、`torch`、`ultralytics` 的 `kjyx2` 环境运行。

## 启动

```powershell
& 'D:\Anaconda\envs\kjyx2\python.exe' 'web-system\backend\server.py'
```

默认地址：

```text
http://127.0.0.1:8099
```

启动后直接打开该地址即可进入前端页面；API 也挂在同一个服务下。

## 接口

- `GET /api/health`
- `GET /api/preset-route`
- `POST /api/predict`
- `POST /api/upload`

视频上传后会保存文件，并通过 `analyzer.py` 调用 YOLOv8 进行全程统计。若监控视频文件名中包含起止时间，系统会用真实时间长度校正 Flow 等时间相关指标，避免加速视频导致误判。
