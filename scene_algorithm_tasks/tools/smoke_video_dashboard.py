"""Verify real MP4 playback, seeking, slow motion and final-candidate labels."""
import json
from pathlib import Path
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

PACK = Path(__file__).resolve().parents[1]
OUT = PACK / "verification/video"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    media = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        for base in ("http://127.0.0.1:8771/", "http://127.0.0.1:8770/scene_algorithm_tasks/"):
            print("Checking " + base, flush=True)
            page.goto(base + "index.html#model=openai_astra&task=SA01_L1", wait_until="networkidle")
            assert page.locator('[data-view="video"]').get_attribute("aria-pressed") == "true"
            assert page.locator("#video-view").is_visible()
            page.wait_for_function("document.querySelector('#final-video')?.readyState >= 2")
            page.locator("#final-video").scroll_into_view_if_needed()
            page.locator("#final-video").evaluate("v=>v.play()")
            page.wait_for_function("document.querySelector('#final-video')?.currentTime > .5")
            properties = page.locator("#final-video").evaluate("v => ({duration:v.duration, width:v.videoWidth, height:v.videoHeight, url:v.currentSrc, loop:v.loop})")
            assert properties["duration"] == 4 and properties["width"] == 1280 and properties["height"] == 720
            page.locator("#video-speed").select_option("0.25")
            assert page.locator("#final-video").evaluate("v=>v.playbackRate") == .25
            page.locator("#final-video").evaluate("v=>{v.pause();v.currentTime=2.5}")
            page.wait_for_function("Math.abs(document.querySelector('#final-video').currentTime-2.5)<.1 && !document.querySelector('#final-video').seeking")
            page.evaluate("window.__videoBeforeRefresh=document.querySelector('#final-video')")
            page.locator("#refresh").click()
            page.wait_for_timeout(600)
            assert page.evaluate("window.__videoBeforeRefresh===document.querySelector('#final-video')")
            assert page.locator("#video-links a[download]").count() == 1
            media.append(properties)
        request = Request(media[0]["url"], headers={"Range": "bytes=100-199"})
        with urlopen(request) as response:
            assert response.status == 206 and len(response.read()) == 100
            assert response.headers["Content-Range"].startswith("bytes 100-199/")
        page.goto("http://127.0.0.1:8771/index.html#model=openai_astra&task=SA01_L3", wait_until="networkidle")
        page.wait_for_function("document.querySelector('#final-video')?.readyState >= 2")
        page.screenshot(path=str(OUT / "desktop.png"), full_page=True)
        page.locator('[data-view="render"]').click()
        assert page.locator("#render-view").is_visible()
        assert page.locator("#final-video").evaluate("v=>v.paused")
        page.locator('[data-view="video"]').click()
        page.locator('.model-tab[data-model="claude_main"]').click()
        assert page.locator("#final-video").count() == 0
        assert page.locator("#video-stage .empty-state").is_visible()
        page.locator('.model-tab[data-model="openai_astra"]').click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(OUT / "mobile.png"), full_page=True)
        page.goto("http://127.0.0.1:8771/index.html", wait_until="networkidle")
        assert page.locator("#final-video").count() == 1
        browser.close()
    assert not errors, errors
    report = {"status": "passed", "both_entries_play": True, "native_mp4": media,
              "default_opens_available_final_video": True, "seek": True, "slow_motion": True, "http_range": True, "refresh_keeps_player": True,
              "queued_empty_state": True, "mobile_no_overflow": True, "browser_errors": errors,
              "model_api_calls": 0}
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
