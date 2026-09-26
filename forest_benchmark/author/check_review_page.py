import json
from pathlib import Path
from urllib.parse import unquote, urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "author/reports/review_page"
out.mkdir(parents=True, exist_ok=True)
errors, records = [], []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((ROOT / "index.html").as_uri())
    for task in [f"{c}_L{l}" for c in "ABCDE" for l in (1, 2)]:
        page.locator(f'nav button[data-id="{task}"]').click()
        page.wait_for_function("['overview','oblique'].every(id=>{const v=document.getElementById(id);return v.readyState>=1&&Number.isFinite(v.duration)})")
        videos = page.locator("video").evaluate_all("vs=>vs.map(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error?.message??null}))")
        assert all(v["duration"] == 6 and v["width"] == 640 and v["height"] == 360 and v["error"] is None for v in videos)
        for tab in ["files", "evidence", "trace", "prompt"]:
            page.locator(f'[data-pane="{tab}"]').click()
            assert page.locator(f"#{tab}").is_visible()
        assert page.locator("#promptText").inner_text().startswith("#")
        links = page.locator("a").evaluate_all("as=>as.map(a=>a.href)")
        missing = []
        for link in links:
            parsed = urlparse(link)
            if parsed.scheme != "file":
                continue
            path = Path(unquote(parsed.path).lstrip("/"))
            if not path.exists():
                missing.append(str(path))
        assert not missing, missing
        records.append({"task": task, "status": "PASS", "videos": videos, "local_links": len(links)})
    page.locator("#play").click()
    page.wait_for_function("document.getElementById('overview').currentTime>.15")
    page.locator("#pause").click()
    page.screenshot(path=str(out / "desktop.png"), full_page=False)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.screenshot(path=str(out / "mobile.png"), full_page=False)
    browser.close()
assert not errors, errors
(out / "report.json").write_text(json.dumps({"status": "PASS", "tasks": records, "page_errors": errors,
                                            "playback": "PASS", "mobile_overflow": False}, indent=2), encoding="utf-8")
print("Review page: 10 tasks, 20 videos, local links, tabs, playback and mobile layout PASS")
