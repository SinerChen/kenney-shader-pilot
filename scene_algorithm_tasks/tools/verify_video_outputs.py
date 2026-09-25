"""Audit encoded final videos without invoking models or GPU rendering."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw

PACK = Path(__file__).resolve().parents[1]
OUT = PACK / "verification/video"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cached_path = OUT / "outputs.json"
    cached = json.loads(cached_path.read_text()) if cached_path.exists() else {"videos": {}}
    records = cached["videos"]
    tiles = []
    for path in sorted((PACK / "runs/s1_p3").glob("*/*/presentation/latest.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if meta["status"] != "ready":
            continue
        key = meta["alias"] + "/" + meta["task_id"]
        movie = PACK / meta["video"]
        assert digest(movie) == meta["video_sha256"], key
        root = path.parent.parent / "model_workspace"
        current = {p.relative_to(root).as_posix(): digest(p) for p in (root / "effect").rglob("*") if p.is_file() and p.name != "plan.json"}
        assert current == meta["candidate_sha256"], key
        if records.get(key, {}).get("sha256") != meta["video_sha256"]:
            command = [shutil.which("ffmpeg"), "-v", "error", "-i", str(movie), "-vf", "scale=160:90",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            raw = subprocess.run(command, capture_output=True, check=True, timeout=60,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).stdout
            frame_bytes = 160 * 90 * 3
            frames = [raw[i:i + frame_bytes] for i in range(0, len(raw), frame_bytes)]
            assert len(frames) == meta["frame_count"], key
            assert all(len(frame) == frame_bytes for frame in frames), key
            unique = len({hashlib.sha256(frame).digest() for frame in frames})
            records[key] = {"sha256": meta["video_sha256"], "decoded_frames": len(frames), "distinct_frames": unique,
                            "duration_seconds": meta["duration_seconds"], "fps": meta["fps"], "candidate_matches": True}
            strip = Image.new("RGB", (480, 112), "#182433")
            ImageDraw.Draw(strip).text((5, 2), key, fill="white")
            for index, frame_index in enumerate((0, len(frames)//2, len(frames)-1)):
                strip.paste(Image.frombytes("RGB", (160, 90), frames[frame_index]), (index * 160, 22))
            strip.save(OUT / (key.replace("/", "_") + ".jpg"))
        tiles.append(Image.open(OUT / (key.replace("/", "_") + ".jpg")))
    if tiles:
        sheet = Image.new("RGB", (960, ((len(tiles)+1)//2)*112), "#182433")
        for i, tile in enumerate(tiles):
            sheet.paste(tile, ((i % 2)*480, (i//2)*112))
        sheet.save(OUT / "contact_sheet.jpg", quality=90)
    final_candidates = 0
    for final_path in (PACK / "runs/s1_p3").glob("*/*/result.json"):
        final = json.loads(final_path.read_text(encoding="utf-8"))
        if final.get("stop_reason") not in ("model_finished", "model_incomplete", "budget_exhausted", "output_truncated"):
            continue
        effect = final_path.parent / "model_workspace/effect"
        hashes = {p.relative_to(effect).as_posix(): digest(p) for p in effect.rglob("*") if p.is_file()}
        assert hashes == final["candidate_files"], str(final_path)
        final_candidates += 1
    approval = json.loads((PACK / "runtime/experiment/approval.json").read_text(encoding="utf-8"))
    for relative, expected in approval["frozen_hashes"].items():
        assert digest(PACK / "runtime/experiment" / relative) == expected, relative
    result = {"status": "passed", "checked": len(records), "model_api_calls": 0,
              "final_candidates_unchanged": final_candidates, "frozen_inputs_unchanged": len(approval["frozen_hashes"]), "videos": records}
    cached_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "videos"}))


if __name__ == "__main__":
    main()
