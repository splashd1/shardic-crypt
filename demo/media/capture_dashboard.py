#!/usr/bin/env python3
"""One-off script: drives a real shardic-envelope ceremony against the
live demo stack (assumes keycloak + combiner + candidates are already
up and trustees registered) while a headless Chrome tab sits on the
dashboard, video-recording the whole thing via Playwright.

Prints a JSON timeline of wall-clock offsets (seconds into the video)
for each named beat, so the continuous recording can be cut into clips
matching walkthrough.tape's `# SPLICE:` points.

Not meant to be re-run unattended without re-checking state -- it pauses
and unpauses specific named containers and assumes a specific starting
ceremony shape (same as demo/README.md's Walkthrough).
"""
import asyncio
import json
import subprocess
import time

from playwright.async_api import async_playwright

DEMO_DIR = "/vb/git/shardic/demo"
VIDEO_DIR = f"{DEMO_DIR}/media/dashboard-recording"


def sh(cmd, timeout=30):
    return subprocess.run(
        cmd, shell=True, cwd=DEMO_DIR, capture_output=True, text=True, timeout=timeout
    )


def operator_token():
    r = sh(
        "curl -s -X POST http://localhost:8080/realms/shardic-demo/protocol/openid-connect/token "
        "-d grant_type=password -d client_id=shardic-operator-client "
        '-d username=operator -d "password=$(grep OPERATOR_PASSWORD .env | cut -d= -f2)" '
        "-d scope=openid"
    )
    return json.loads(r.stdout)["access_token"]


async def main():
    timeline = {}
    t0 = None

    def mark(name):
        elapsed = round(time.monotonic() - t0, 2)
        timeline[name] = elapsed
        print(f"[{elapsed:7.2f}s] {name}")

    token = operator_token()

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1000},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1280, "height": 1000},
        )
        page = await context.new_page()

        t0 = time.monotonic()
        await page.goto("http://localhost:5000/dashboard")
        mark("dashboard_open_trustees_registering")

        # Fill the operator token field (mirrors a presenter pasting it in;
        # the dashboard doesn't need it to *display* state -- only its own
        # buttons need it -- but fill it in for realism and for the Verify
        # click at the end).
        await page.fill("#admin-token", token)
        await page.wait_for_timeout(3000)
        mark("trustees_registered")

        # --- Step 4: pause erin, initiate the ceremony ---
        sh("docker-compose pause trustee-erin")
        await page.wait_for_timeout(1500)
        mark("erin_paused")

        sh(
            "curl -s -X POST -H \"Authorization: Bearer %s\" -H 'Content-Type: application/json' "
            "-d '{\"threshold_d\": 3, \"prime\": \"alice\", \"pool\": [\"bob\", \"carol\", \"dave\", \"erin\"], \"backups\": [\"frank\"]}' "
            "http://localhost:5000/admin/ceremony/initiate" % token
        )
        await page.wait_for_timeout(2000)
        mark("ceremony_initiated")

        # --- Step 5: live watch -- TTL expiry, backfill, frank accepts, formed ---
        for _ in range(30):
            text = await page.locator("#ceremony-log").inner_text()
            if "formed" in text.lower():
                break
            await page.wait_for_timeout(1000)
        mark("ceremony_formed")

        sh("docker unpause demo_trustee-erin_1")
        await page.wait_for_timeout(1000)
        mark("erin_unpaused")

        # --- Step 6: create the vault ---
        sh(f'curl -s -X POST -H "Authorization: Bearer {token}" http://localhost:5000/admin/vault/create')
        await page.wait_for_timeout(2000)
        mark("vault_created")

        # --- Step 8: pause dave + frank (threshold proof) ---
        sh("docker-compose pause trustee-dave trustee-frank")
        await page.wait_for_timeout(1500)
        mark("dave_frank_paused")

        # --- Step 9: trigger recovery, watch shards arrive ---
        sh(f'curl -s -X POST -H "Authorization: Bearer {token}" http://localhost:5000/admin/recovery/start')
        await page.wait_for_timeout(1000)
        mark("recovery_started")

        for _ in range(20):
            text = await page.locator("#shard-pool-count").inner_text()
            if text.strip() == "2":
                break
            await page.wait_for_timeout(1000)
        await page.wait_for_timeout(1000)
        mark("shards_all_in")

        # --- Step 10: finalize ---
        sh(f'curl -s -X POST -H "Authorization: Bearer {token}" http://localhost:5000/admin/recovery/finalize')
        await page.wait_for_timeout(2000)
        mark("finalized")

        # --- Step 11 + verify banner beat ---
        sh(
            "docker exec $(docker-compose ps -q combiner) sh -c "
            "'diff -r /data/sample-secret /data/recovered/sample-secret && echo MATCH'"
        )
        await page.wait_for_timeout(1000)
        mark("byte_diff_checked_dashboard_still_pending")

        await page.click("#btn-verify")
        await page.wait_for_timeout(2000)
        mark("verified")

        await page.wait_for_timeout(1500)
        await context.close()
        await browser.close()

    with open(f"{DEMO_DIR}/media/dashboard-timeline.json", "w") as f:
        json.dump(timeline, f, indent=2)
    print("\ntimeline written to media/dashboard-timeline.json")


asyncio.run(main())
