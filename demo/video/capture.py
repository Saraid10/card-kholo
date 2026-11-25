"""Capture 1920x1080 screenshots of the live Card Kholo app with headless Chrome (DevTools protocol).

Usage: python demo/video/capture.py [WEB_URL] [API_URL]
Uses a throwaway Chrome profile; writes PNGs to demo/video/shots/.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from websockets.sync.client import connect

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHOTS = HERE / "shots"
WEB = (sys.argv[1] if len(sys.argv) > 1 else "https://card-kholo.vercel.app").rstrip("/")
API = (sys.argv[2] if len(sys.argv) > 2 else "https://card-kholo-api.onrender.com").rstrip("/")
CHROME = next(p for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                          shutil.which("chromium") or "", shutil.which("google-chrome") or ""] if p and Path(p).exists())
PORT = 9333


class Page:
    def __init__(self, ws_url):
        self.ws = connect(ws_url, max_size=64 * 2**20, open_timeout=30)
        self.n = 0

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv(timeout=90))
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        return r.get("result", {}).get("value")

    def go(self, path, settle=2.5):
        self.call("Page.navigate", url=WEB + path)
        for _ in range(60):
            time.sleep(0.25)
            if self.js("document.readyState") == "complete":
                break
        time.sleep(settle)

    def wait_for(self, expr, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if self.js(expr):
                return True
            time.sleep(0.5)
        raise TimeoutError(expr)

    def click_text(self, text):
        ok = self.js(f"""(() => {{
            const t = {json.dumps(text)};
            const el = [...document.querySelectorAll('button,a,[role=button]')]
              .find(e => (e.innerText || e.getAttribute('aria-label') || '').trim().includes(t));
            if (!el) return false; el.scrollIntoView({{block: 'center'}}); el.click(); return true; }})()""")
        if not ok:
            raise RuntimeError(f"No button with text {text!r}")

    def upload(self, path):
        doc = self.call("DOM.getDocument", depth=-1)
        node = self.call("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector="input[type=file]")
        self.call("DOM.setFileInputFiles", nodeId=node["nodeId"], files=[str(path)])

    def shot(self, name):
        self.js("window.scrollTo(0, 0)")
        time.sleep(0.4)
        data = self.call("Page.captureScreenshot", format="png")["data"]
        import base64
        (SHOTS / f"{name}.png").write_bytes(base64.b64decode(data))
        print("  shot", name)


def identify(name, lang, role, beta=False):
    r = httpx.post(f"{API}/api/identify", json={"name": name, "lang": lang, "role": role, "beta": beta}, timeout=90)
    r.raise_for_status()
    j = r.json()
    return {"user_id": j["user_id"], "name": name, "lang": lang, "role": role, "beta": beta, "pair_link": j["pair_link"]}


def set_user(p, user):
    p.js(f"localStorage.setItem('cardkholo_user', {json.dumps(json.dumps(user))}); true")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    httpx.get(f"{API}/health", timeout=90)  # wake Render
    profile = tempfile.mkdtemp(prefix="ck-chrome-")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                             "--no-first-run", "--hide-scrollbars", "--mute-audio", "--autoplay-policy=user-gesture-required",
                             "--window-size=1440,810", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                targets = httpx.get(f"http://127.0.0.1:{PORT}/json/list", timeout=2).json()
                page = next(t for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.5)
        p = Page(page["webSocketDebuggerUrl"])
        p.call("Page.enable")
        p.call("Emulation.setDeviceMetricsOverride", width=1440, height=810, deviceScaleFactor=1.3333334, mobile=False)

        print("landing + welcome")
        p.go("/", settle=3)
        p.js("localStorage.clear(); true")
        p.go("/", settle=3)
        p.shot("01_landing")
        p.go("/start", settle=2)
        p.shot("02_start")

        user = identify("Sunita Agarwal", "en", "parent")
        set_user(p, user)
        print("link family")
        p.go("/link", settle=3)
        p.shot("03_link")

        print("real card")
        p.go("/check", settle=2)
        p.shot("04_check")
        p.upload(ROOT / "demo" / "Priya_Arjun_Wedding_Card.pdf")
        p.wait_for("location.pathname.startsWith('/result/')", timeout=60)
        time.sleep(3)
        p.shot("05_result_ok")
        p.click_text("See my functions")
        p.wait_for("location.pathname === '/calendar'")
        time.sleep(3)
        p.shot("06_calendar")
        p.go("/directions/0", settle=7)
        p.shot("07_directions")

        print("fake apk")
        p.go("/check", settle=2)
        p.upload(ROOT / "demo" / "Shaadi_Card_Priya.pdf.apk")
        p.wait_for("location.pathname.startsWith('/result/')", timeout=60)
        time.sleep(3)
        p.shot("08_stop")
        p.click_text("already opened")
        p.wait_for("location.pathname.startsWith('/first-hour/')")
        time.sleep(3)
        p.shot("09_first_hour")

        print("suspicious link")
        p.go("/check", settle=2)
        p.js("""(() => { const t = document.querySelector('textarea');
            const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
            set.call(t, 'Shaadi ka card yahan dekho: http://bit.ly/priya-card-2026');
            t.dispatchEvent(new Event('input', {bubbles: true})); return true; })()""")
        time.sleep(0.5)
        p.click_text("Check")
        p.wait_for("location.pathname.startsWith('/result/')", timeout=60)
        time.sleep(2)
        p.shot("10_check_link")

        print("hindi stop")
        hindi = identify("Kamla Devi", "hi", "parent")
        set_user(p, hindi)
        p.go("/check", settle=2)
        p.upload(ROOT / "demo" / "Shaadi_Card_Priya.pdf.apk")
        p.wait_for("location.pathname.startsWith('/result/')", timeout=60)
        time.sleep(3)
        p.shot("11_stop_hindi")

        print("checked today + status + host")
        set_user(p, user)
        p.go("/check", settle=3)
        p.shot("12_checked_today")
        p.go("/status", settle=6)
        p.shot("13_status")
        host = identify("Ramesh Agarwal", "en", "host")
        set_user(p, host)
        p.go("/host", settle=3)
        p.shot("14_host")
    finally:
        proc.terminate()
        time.sleep(1)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
