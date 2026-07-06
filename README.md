# Muninn Clip Worker

Small HTTP service that trims a YouTube segment with `yt-dlp` + `ffmpeg` and returns the resulting mp4 as bytes. Exists so devices without shell access (Android) can still capture real clips: every client just calls this over HTTPS.

## Endpoints

- `GET /health` → `{"ok": true}`, no auth, for checking the deploy worked.
- `POST /clip` → body `{"url": "...", "start": "12:34", "end": "15:02"}`, header `Authorization: Bearer <AUTH_TOKEN>`, returns the mp4 file as the response body.

## Deploy (Render.com, free)

1. Push this `clip-worker/` folder to a new GitHub repo.
2. On [render.com](https://render.com): **New +** → **Blueprint** → connect the repo. Render reads `render.yaml` and provisions the service automatically on the free plan.
3. Once deployed, open the service → **Environment** tab → copy the auto-generated `AUTH_TOKEN` value.
4. Copy the service's public URL (something like `https://muninn-clip-worker.onrender.com`).
5. Paste both into `WORKER_URL` / `AUTH_TOKEN` in `05-Templates/Scripts/download-clip.js` in the vault.
6. Test: visit `<your-url>/health` in a browser — should return `{"ok":true}`.

## Notes

- Free Render services spin down after ~15 min idle and take 30-50s to cold-start on the next request — expect a delay on the first capture after a break, not a failure.
- Keep clips short. `subprocess` has a 600s timeout, and very long downloads risk platform request limits.
- This downloads YouTube video data, which runs against YouTube's Terms of Service even for personal use. Treat output as private notes, not redistribution — don't make this endpoint or its output public.
- The `AUTH_TOKEN` is the only thing standing between this endpoint and the open internet. Don't commit it to the repo (it isn't — `render.yaml` only generates it as an env var) and don't share the URL+token together.
