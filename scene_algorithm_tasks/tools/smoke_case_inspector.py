"""Exercise inline prompts, event browsing and actual code diffs in both viewers."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PACK = Path(__file__).resolve().parents[1]
OUT = PACK / "verification/case_inspector"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    errors, bad_responses = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: bad_responses.append([response.status, response.url]) if response.status >= 400 and not response.url.endswith("favicon.ico") else None)
        for base in ("http://127.0.0.1:8771/", "http://127.0.0.1:8770/scene_algorithm_tasks/"):
            page.goto(base + "index.html#model=openai_astra&task=SA01_L1", wait_until="networkidle")
            page.locator('[data-view="prompt"]').click()
            page.wait_for_selector("#prompt-body details")
            expected = json.loads((PACK / "runs/s1_p3/openai_astra/SA01_L1/input.json").read_text(encoding="utf-8"))
            assert page.locator("#prompt-body details pre").nth(0).text_content() == expected["messages"][0]["content"]
            assert page.locator("#prompt-body details pre").nth(1).text_content() == expected["messages"][1]["content"]
            assert "实际发送" in page.locator("#prompt-body").inner_text()

            page.locator('[data-view="files"]').click()
            page.wait_for_selector("#file-code pre")
            assert page.locator(".diff-add").count() > 0
            assert page.locator(".diff-remove").count() > 0
            page.locator('[data-mode="current"]').click()
            actual = (PACK / "runs/s1_p3/openai_astra/SA01_L1/model_workspace/effect/main.gd").read_text(encoding="utf-8")
            assert page.locator("#file-code pre").text_content() == actual
            page.locator('[data-mode="before"]').click()
            initial = (PACK / "runs/s1_p3/openai_astra/SA01_L1/initial_effect/main.gd").read_text(encoding="utf-8")
            assert page.locator("#file-code pre").text_content() == initial
            page.locator(".write-history button").first.click()
            page.wait_for_selector(".trace-event[open] .event-body pre")
            assert "写入的完整内容" in page.locator(".trace-event[open]").inner_text()
            page.locator("#trace-filter").select_option("error")
            assert page.locator(".trace-event").count() > 0
            page.locator(".trace-event summary").first.click()
            page.wait_for_function("document.querySelector('.trace-event[open] .event-body')?.textContent.includes('First operation')")
            page.locator("#trace-filter").select_option("render")
            page.locator(".trace-event summary").last.click()
            page.wait_for_function("document.querySelector('.trace-event[open] img')?.naturalWidth > 0")
            page.locator("#trace-filter").select_option("all")
            page.locator("#trace-next").click()
            assert "2 /" in page.locator("#trace-page").inner_text()
            page.locator("#trace-search").fill("grass_geometry.gd")
            assert page.locator(".trace-event").count() > 0
            page.locator("#trace-search").fill("")

            page.locator('.level-button[data-task="SA01_L2"]').click()
            page.locator('[data-view="files"]').click()
            page.wait_for_function("document.querySelector('#files-body')?.textContent.includes('实际继承的 SA01_L1')")
            page.wait_for_selector("#file-code pre")
            page.locator('[data-mode="diff"]').click()
            page.screenshot(path=str(OUT / "files_desktop.png"), full_page=True)
            page.locator('.model-tab[data-model="claude_main"]').click()
            page.locator('[data-view="prompt"]').click()
            page.wait_for_function("document.querySelector('#prompt-body')?.textContent.includes('尚未调用模型')")
            page.locator('[data-view="trajectory"]').click()
            assert page.locator("#trajectory-body .empty-state").is_visible()

        page.locator('.model-tab[data-model="openai_astra"]').click()
        page.locator('[data-view="files"]').click()
        page.wait_for_selector("#file-code pre")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile overflow"
        page.screenshot(path=str(OUT / "files_mobile.png"), full_page=True)
        browser.close()
    assert not errors, errors
    assert not bad_responses, bad_responses
    report = {"status": "passed", "exact_prompt": True, "initial_and_current_contents": True,
              "diff": True, "write_to_event_jump": True, "event_filters_search_paging": True,
              "render_feedback_images": True, "inheritance_baseline": True, "queued_preview": True,
              "both_entries": True, "mobile_no_overflow": True, "browser_errors": errors,
              "http_errors": bad_responses, "model_api_calls": 0}
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
