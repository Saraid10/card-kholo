"""Trigger the false-alarm incident through the public API only (never Flagsmith or NudgeBee directly).

Usage: .venv\\Scripts\\python scripts\\simulate_incident.py https://your-backend.onrender.com
"""

import io
import json
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageDraw


def harmless_pdf(index: int) -> bytes:
    demo = Path(__file__).resolve().parents[1] / "demo" / f"invitation_card_{index}.pdf"
    if demo.exists():  # made by demo/make_real_card.py
        return demo.read_bytes()
    page = Image.new("RGB", (600, 800), "white")
    ImageDraw.Draw(page).text((40, 40), f"Card Kholo test invitation {index}. Harmless.", fill="black")
    buffer = io.BytesIO()
    page.save(buffer, format="PDF")
    return buffer.getvalue()


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: simulate_incident.py <base_url>")
    base = sys.argv[1].rstrip("/")
    with httpx.Client(base_url=base, timeout=60) as client:
        user = client.post("/api/identify", json={"name": "Incident Demo", "lang": "en", "role": "parent", "beta": True})
        user.raise_for_status()
        user_id = user.json()["user_id"]
        print(f"1. Identified a beta parent ({user_id[:8]}…)")

        scans = []
        for i in (1, 2, 3):
            name = f"invitation_card_{i}.pdf"
            response = client.post("/api/scan", data={"user_id": user_id},
                                   files={"file": (name, harmless_pdf(i), "application/pdf")})
            response.raise_for_status()
            scan = response.json()
            hit = "pack_broad_test" in scan["pack_hits"]
            print(f"2. {name}: {scan['verdict']} pack_hits={scan['pack_hits']}")
            if scan["verdict"] != "DANGEROUS" or not hit:
                print("   Not flagged by pack_broad_test. Likely causes:\n"
                      "   - pack_broad_test has no canary_20 override, or canary_20 lacks the rule beta = true\n"
                      "   - the pack was already rolled back (environment default OFF, override deleted): re-add it\n"
                      "   - scam_signatures has no rule with pack pack_broad_test matching 'invitation'\n"
                      "   - the backend cannot reach Flagsmith (it then uses local defaults: pack_broad_test OFF)")
            scans.append(scan)

        for scan in scans:
            response = client.post("/api/feedback", json={"scan_id": scan["scan_id"], "real_invite": True})
            response.raise_for_status()
            print(f"3. Feedback 'real invite' -> {response.json()['pack_false_alarms']}")

        status = client.get("/api/status").json()
        print("4. Packs:")
        for pack in status["packs"]:
            print(f"   {pack['name']:<20} enabled={pack['enabled']!s:<5} false_alarms_5m={pack['false_alarms_5m']}")
        print("   Incidents:")
        for incident in status["incidents"][:5]:
            print("   " + json.dumps(incident))
        if not any(i["pack"] == "pack_broad_test" and i["status"] == "open" for i in status["incidents"]):
            print("   No open pack_broad_test incident. If one was already open or rolled back in the last"
                  " 5 minutes, reset first (see the reset checklist in README.md).")
        else:
            print("   Open incident created. Approve it in NudgeBee (or use Plan B: fallback-rollback).")


if __name__ == "__main__":
    main()
