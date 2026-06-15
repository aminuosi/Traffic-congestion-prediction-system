from pathlib import Path


def iter_boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    cursor = start
    while cursor + 8 <= end:
        size = int.from_bytes(data[cursor : cursor + 4], "big")
        box_type = data[cursor + 4 : cursor + 8].decode("latin1", errors="replace")
        header = 8
        if size == 1 and cursor + 16 <= end:
            size = int.from_bytes(data[cursor + 8 : cursor + 16], "big")
            header = 16
        if size == 0:
            size = end - cursor
        if size < header or cursor + size > end:
            break
        yield box_type, cursor, cursor + size, header
        cursor += size


def find_box(data, path, start=0, end=None):
    boxes = [(start, len(data) if end is None else end)]
    for name in path:
        next_boxes = []
        for box_start, box_end in boxes:
            for box_type, start_at, end_at, header in iter_boxes(data, box_start, box_end):
                if box_type == name:
                    next_boxes.append((start_at + header, end_at))
        boxes = next_boxes
    return boxes


def probe_mp4(path):
    path = Path(path)
    data = path.read_bytes()
    brands = []
    codecs = []
    ftyp = find_box(data, ["ftyp"])
    if ftyp:
        start, end = ftyp[0]
        major = data[start : start + 4].decode("latin1", errors="replace")
        brands.append(major)
        for index in range(start + 8, end, 4):
            brands.append(data[index : index + 4].decode("latin1", errors="replace"))

    for stsd_start, stsd_end in find_box(data, ["moov", "trak", "mdia", "minf", "stbl", "stsd"]):
        cursor = stsd_start + 8
        while cursor + 8 <= stsd_end:
            size = int.from_bytes(data[cursor : cursor + 4], "big")
            codec = data[cursor + 4 : cursor + 8].decode("latin1", errors="replace")
            if size < 8:
                break
            codecs.append(codec)
            cursor += size

    return {
        "path": str(path),
        "size": path.stat().st_size,
        "brands": brands,
        "codecs": codecs,
    }


if __name__ == "__main__":
    import json
    import sys

    for item in sys.argv[1:]:
        print(json.dumps(probe_mp4(item), ensure_ascii=False, indent=2))
