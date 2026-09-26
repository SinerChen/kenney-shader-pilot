"""Check actual native-baseline playback and blocked-task presentation."""
import json
from pathlib import Path
from urllib.parse import urlparse,unquote
from playwright.sync_api import sync_playwright
from l3_source import ROOT,TASKS,dump


def check():
    out=ROOT/"author/reports/review_page/l3";out.mkdir(parents=True,exist_ok=True)
    records=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="msedge",headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1100})
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto((ROOT/"index.html").as_uri())
        assert page.locator("nav button").count()==16
        for task in TASKS:
            page.locator(f'nav button[data-id="{task}"]').click()
            blocked=task=="C_L3_S"
            if blocked:
                assert not page.locator("#videoGrid").is_visible()
                assert "BLOCKED_SOURCE" in page.locator("#facts").inner_text()
                video=None
            else:
                page.wait_for_function("(()=>{const v=document.getElementById('overview');return v.readyState>=1&&Number.isFinite(v.duration)})()")
                video=page.locator("#overview").evaluate("v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,error:v.error?.message??null})")
                assert video=={"duration":2,"width":640,"height":360,"error":None},video
                assert not page.locator("#oblique").is_visible()
                page.locator("#play").click()
                page.wait_for_function("document.getElementById('overview').currentTime>.15")
                assert page.locator("#oblique").evaluate("v=>v.paused")
                page.locator("#pause").click()
            links=[]
            for tab in ["files","evidence","trace","prompt"]:
                page.locator(f'[data-pane="{tab}"]').click()
                assert page.locator(f"#{tab}").is_visible()
                links+=page.locator("a:visible").evaluate_all("as=>as.map(a=>a.href)")
            missing=[]
            for link in set(links):
                parsed=urlparse(link)
                if parsed.scheme=="file" and not Path(unquote(parsed.path).lstrip("/")).exists():missing.append(link)
            assert not missing,missing
            page.evaluate("window.scrollTo(0,0)")
            if task in ["A_L3","C_L3_S"]:page.screenshot(path=str(out/(task+".png")))
            records.append({"task":task,"status":"PASS","video":video,"visible_local_links":len(set(links))})
        page.set_viewport_size({"width":390,"height":844})
        page.locator('nav button[data-id="B_L3"]').click()
        assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
        page.screenshot(path=str(out/"mobile.png"))
        # Returning to a prior task restores both legacy video elements.
        page.locator('nav button[data-id="A_L1"]').click()
        assert page.locator("#oblique").is_visible()
        browser.close()
    assert not errors,errors
    result={"status":"PASS","tasks":records,"page_errors":errors,"mobile_overflow":False,"legacy_navigation_restored":True}
    dump(out/"report.json",result)
    print("L3 page: 16 navigation entries, 5 native videos, blocked source, links, playback and mobile PASS")


if __name__=="__main__":check()
