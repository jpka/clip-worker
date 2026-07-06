# Muninn Clip Worker

Small HTTP service that trims a YouTube segment with `yt-dlp` + `ffmpeg` and returns the resulting mp4 as bytes. Exists so devices without shell access (Android) can still capture real clips: every client just calls this over HTTPS.

## Endpoints

- `GET /health` -> `{"ok": true, "cookies_configured": true|false}`, no auth, for checking the deploy worked.
- `POST /clip` -> body `{"url": "...", "start": "12:34", "end": "15:02"}`, header `Authorization: Bearer <AUTH_TOKEN>`, returns the mp4 file as the response body.

## Deploy (Render.com, free)

1. Push this `clip-worker/` folder to a new GitHub repo.
2. On [render.com](https://render.com): **New +** -> **Blueprint** -> connect the repo. Render reads `render.yaml` and provisions the service automatically on the free plan.
3. Once deployed, open the service -> **Environment** tab -> copy the auto-generated `AUTH_TOKEN` value.
4. Copy the service's public URL (something like `https://muninn-clip-worker.onrender.com`).
5. Paste both into `WORKER_URL` / `AUTH_TOKEN` in `05-Templates/Scripts/download-clip.js` in the vault.
6. Test: visit `<your-url>/health` in a browser -- should return `{"ok":true,...}`.

## YouTube cookies (needed to avoid 429s)

YouTube rate-limits and partially blocks anonymous requests, especially from cloud-provider IP ranges. Passing cookies from a real, logged-in browser session makes requests look like an ordinary logged-in user and cuts this down a lot (though it may not eliminate it entirely -- see Notes).

1. Install a cookie-export extension in your browser, e.g. "Get cookies.txt LOCALLY" (Chrome/Firefox), while logged into youtube.com.
2. Export cookies for youtube.com as a `cookies.txt` file (Netscape format).
3. On Render: open the service -> **Environment** tab -> **Secret Files** -> add a file named `cookies.txt`, path `/etc/secrets/cookies.txt`, paste the file's contents.
4. Redeploy (Render does this automatically when a secret file is saved). Check `/health` -- `cookies_configured` should now be `true`.
5. Cookies expire (weeks to months). If 429/403 errors come back, re-export and re-upload.

## Notes

- Free Render services spin down after ~15 min idle and take 30-50s to cold-start on the next request -- expect a delay on the first capture after a break, not a failure.
- Keep clips short. `subprocess` has a 600s timeout, and very long downloads risk platform request limits.
- Even with cookies and Deno installed (for solving YouTube's JS signature challenges), a shared/free host's IP range can still get flagged by YouTube -- this is IP reputation, not something cookies alone fix. If 429s persist after adding cookies, the next lever is a paid plan with a dedicated IP, or routing requests through a proxy; worth revisiting if this keeps happening rather than assuming the config is wrong.
- This downloads YouTube video data, which runs against YouTube's Terms of Service even for personal use. Treat output as private notes, not redistribution -- don't make this endpoint or its output public.
- The `AUTH_TOKEN` is the only thing standing between this endpoint and the open internet. Don't commit it to the repo (it isn't -- `render.yaml` only generates it as an env var) and don't share the URL+token together.
