"""Check the local dashboard in an isolated headless browser; no experiment actions."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PACK = Path(__file__).resolve().parents[1]
OUT = PACK / "verification/dashboard"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    data = json.loads((PACK / "runtime/dashboard.json").read_text(encoding="utf-8"))
    errors, bad_responses = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: bad_responses.append([response.status, response.url]) if response.status >= 400 else None)
        page.goto("http://127.0.0.1:8771/index.html", wait_until="networkidle")
        assert page.locator(".model-tab").count() == 4
        assert page.locator(".level-button").count() == 15
        assert page.locator(".matrix-button").count() == 60
        assert str(data["summary"]["completed"]) in page.locator("#metric-completed").inner_text()
        assert "HTTP" in page.locator("#notice").inner_text()
        page.wait_for_function("document.querySelector('#image-stage img')?.naturalWidth > 0")
        page.screenshot(path=str(OUT / "desktop.png"), full_page=True)

        page.locator('.model-tab[data-model="openai_astra"]').click()
        page.locator('.level-button[data-task="SA01_L1"]').click()
        page.wait_for_function("document.querySelector('#image-stage img')?.naturalWidth > 0")
        assert "交互场" in page.locator("#task-title").inner_text()
        page.locator('[data-view="render"]').click()
        initial = page.locator("#image-stage img").get_attribute("src")
        page.locator("#frames button[data-frame]").last.click()
        assert page.locator("#image-stage img").get_attribute("src") != initial
        page.locator("#play-frames").click()
        page.wait_for_timeout(1000)
        page.locator("#play-frames").click()
        run = next(run for run in data["runs"] if run["alias"] == "openai_astra" and run["task_id"] == "SA01_L1")
        failed = next(render for render in run["renders"] if render["ok"] is False)
        page.locator("#render-select").select_option(failed["id"])
        assert page.locator("#render-errors").inner_text().strip()
        assert "本次执行失败" in page.locator("#render-caption").inner_text()
        page.locator('[data-view="plan"]').click()
        assert page.locator("#plan-content .plan-step").count() > 0
        page.locator("#plan-content .plan-step summary").first.click()
        assert page.locator("#plan-content .plan-step[open] dd").first.is_visible()
        page.locator('[data-view="files"]').click()
        page.wait_for_selector("#file-detail .resource-links a")
        assert page.locator("#files-content button").count() > 0
        assert page.locator("#run-links a[download]").count() == 1

        page.locator('.model-tab[data-model="claude_main"]').click()
        page.locator('[data-view="render"]').click()
        assert "尚未执行" in page.locator("#image-stage").inner_text()
        assert page.locator("#image-stage img").count() == 0

        page.locator('.matrix-button[data-model="openai_main"][data-task="SA04_L3"]').click()
        assert "401" in page.locator("#task-error").inner_text()
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile page overflows viewport"
        page.screenshot(path=str(OUT / "mobile.png"), full_page=True)

        page.goto("http://127.0.0.1:8770/scene_algorithm_tasks/index.html#model=openai_astra&task=SA01_L1", wait_until="networkidle")
        assert "GPT-6 Astra" in page.locator("#task-id").inner_text()
        page.wait_for_function("document.querySelector('#image-stage img')?.naturalWidth > 0")
        browser.close()
    assert not errors, errors
    assert not bad_responses, bad_responses
    report = {"status": "passed", "models": 4, "tasks": 60, "model_switch": True, "task_switch": True,
              "render_history": True, "frame_controls": True, "plan_and_files": True,
              "queued_empty_state": True, "paused_401_state": True, "mobile_no_overflow": True,
              "both_http_entries": True, "browser_errors": errors, "failed_http_responses": bad_responses,
              "screenshots": ["desktop.png", "mobile.png"], "model_api_calls": 0}
    (OUT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
