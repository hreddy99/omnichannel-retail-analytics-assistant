# Recording your presentation on a Windows laptop

You're switching between **PowerPoint** (slides) and a **browser** (the live app), so you want a
recorder that captures your **whole screen + your mic** (and optionally your webcam). Three good
options, easiest → most polished.

## Recommended: record the whole thing in one screen capture

### Option A — Zoom (easiest, most reliable) ✅ recommended for a one-take
You already likely have Zoom. It captures everything you do on screen + your voice + a small webcam tile.
1. **New Meeting** (just you) → **Share Screen** → pick **Screen / Desktop** (not a single window, so
   tab-switching is captured).
2. Click **Record** → **Record on this Computer**.
3. Present: run PowerPoint in Slide Show, switch to the browser for the demo, switch back.
4. **Stop Recording** → **End Meeting** → Zoom converts it to an **.mp4** automatically.
- Pros: zero learning curve, captures app + slides + voice + webcam, one file.
- Tip: turn on **Settings → Recording → Optimize for third-party video editor** for clean 1080p; enable
  "Record video during screen sharing" so your webcam tile appears.

### Option B — OBS Studio (free, best quality, webcam overlay) — if you want it to look pro
Download from obsproject.com (free, no watermark, no time limit).
1. Sources: **+ Display Capture** (your screen) → **+ Video Capture Device** (webcam, drag to a corner)
   → **+ Audio Input Capture** (your mic).
2. Set **Settings → Output → Recording Quality: High**, Format **mp4**, ~1080p/30fps.
3. **Start Recording**, present, **Stop Recording**. File lands in Videos by default.
- Pros: best image quality, picture-in-picture webcam, full control. Slightly more setup.

### Option C — Xbox Game Bar (built into Windows 10/11, zero install)
Press **Win + G** → **Capture** widget → **Record** (or **Win + Alt + R** to start/stop). Mic toggle is
in the same widget.
- Good for a quick capture, **but** it records only the **active app window**, so switching between
  PowerPoint and the browser can drop frames or stop. Use only if you can keep everything in one window.

---

## Alternative: let PowerPoint record the slides, screen-record only the demo
PowerPoint has a built-in narration recorder that's excellent for the **slide** portions:
- **Slide Show → Record** (or **Record Slide Show**) → record voice (and webcam, top-right) slide by
  slide; re-record any slide you flub.
- Then **File → Export → Create a Video** → 1080p → **.mp4**.
- Record the **live app demo** separately (Zoom/OBS) and stitch the two clips in the free **Microsoft
  Clipchamp** (preinstalled on Windows 11) or **Photos** app.
- More editing, but you can perfect each slide. Good if you want retakes without redoing the demo.

---

## Settings & tips that make a real difference
- **Resolution:** record at **1920×1080**. Set Windows **Display scale to 100%** while recording so app
  text isn't huge/blurry; zoom the browser to ~110–125% instead.
- **Audio:** use a **headset/earbuds mic**, not the laptop mic — biggest quality win. Record in a quiet
  room; do a 10-second test and play it back before the real take.
- **Close the noise:** quit Slack/Teams/email, silence notifications (**Win + N → Do Not Disturb**),
  close extra tabs. Plug in the charger.
- **Warm up the app first** so the first investigation isn't the slow one on camera.
- **Webcam:** small tile in a bottom corner adds presence; keep your eyes near the camera, not the screen.
- **Do a 60-second rehearsal recording** of slide 1 + the start of the demo, watch it, then record for real.
- **One take is fine** — minor stumbles are normal. If you need to redo a bit, pause, breathe, and repeat
  the sentence; trim later in Clipchamp.
- **Length:** keep it to ~20 minutes. Export, then **watch the whole file once** before submitting to
  confirm audio + screen are both captured.

### Fastest path if you're short on time
Zoom → New Meeting → Share full screen → Record on this Computer → present slides + demo in one go →
End Meeting → submit the .mp4. Done.
