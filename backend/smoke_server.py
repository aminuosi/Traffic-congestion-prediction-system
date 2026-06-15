import json
import threading
import time
import urllib.request

import server


def main():
    httpd = server.ThreadingHTTPServer((server.HOST, 0), server.ApiHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)

    base = f"http://{server.HOST}:{port}"
    with urllib.request.urlopen(base + "/api/health", timeout=5) as response:
        health = json.loads(response.read().decode("utf-8"))
    assert health["ok"] is True

    with urllib.request.urlopen(base + "/api/preset-route", timeout=5) as response:
        route = json.loads(response.read().decode("utf-8"))
    assert route["name"] == "长深高速东庐山服务区示范路段"

    with urllib.request.urlopen(base + "/api/dependencies", timeout=30) as response:
        dependencies = json.loads(response.read().decode("utf-8"))
    assert "ready" in dependencies

    payload = json.dumps({"route": route}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base + "/api/predict",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        prediction = json.loads(response.read().decode("utf-8"))
    assert prediction["status"] == "建议开启应急车道"

    with urllib.request.urlopen(base + "/", timeout=5) as response:
        html = response.read().decode("utf-8")
    assert "智行枢纽" in html

    request = urllib.request.Request(
        base + "/media/preset/2_1_20240501_20240501115227_20240501130415_115227.mp4",
        headers={"Range": "bytes=0-15"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        media_chunk = response.read()
    assert response.status == 206
    assert len(media_chunk) == 16

    with urllib.request.urlopen(
        base + "/preview/preset/2_1_20240501_20240501115227_20240501130415_115227.mp4",
        timeout=10,
    ) as response:
        preview_chunk = response.read(256)
    assert response.status == 200
    assert b"Content-Type: image/jpeg" in preview_chunk

    payload = json.dumps({"filename": "not-found.mp4"}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base + "/api/analyze-video",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as error:
        assert error.code == 404

    httpd.shutdown()
    print("server smoke passed")


if __name__ == "__main__":
    main()
