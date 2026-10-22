# 03 · Authentication (APS OAuth v2, 3-legged)

## What's already set up
- An **APS app** (custom integration) with a client ID, a client secret and the callback URL `http://localhost:8080/`.
- The app is **activated in Forma**: Account Admin → Custom Integrations → client ID added. Without this, every Forma API returns 403.

## `.env` variables
| Variable | Example | Notes |
|---|---|---|
| `APS_CLIENT_ID` | `<client id>` | From aps.autodesk.com → My Apps |
| `APS_CLIENT_SECRET` | `••••` | **Secret.** Local `.env` only |
| `APS_CALLBACK_URL` | `http://localhost:8080/` | Must match the app setting *exactly* (trailing slash included) |
| `AUTODESK_FORMA_API_BASE_URL` | `https://developer.api.autodesk.com` | |
| `APS_SCOPES` | `data:read user-profile:read` | Least privilege for phase 1. Phase 2 adds `data:write` |
| `FORMA_HUB_ID` / `FORMA_PROJECT_ID` | `b.1234…` | From `python fomo1.py hubs` / `projects` |
| `FORMA_REGION` | blank / `EMEA` / `AUS` | Sent as `x-ads-region` header to Issues |

## Flow
1. `python fomo1.py login` starts a tiny local web server on port 8080 and opens:
   `GET https://developer.api.autodesk.com/authentication/v2/authorize?response_type=code&client_id=…&redirect_uri=http://localhost:8080/&scope=data:read user-profile:read&state=<random>`
2. User signs in with their Autodesk account and approves.
3. Browser is redirected to `http://localhost:8080/?code=…&state=…`; the script checks `state`.
4. Code exchange: `POST /authentication/v2/token` with
   `Authorization: Basic base64(client_id:client_secret)`, `Content-Type: application/x-www-form-urlencoded`,
   body `grant_type=authorization_code&code=…&redirect_uri=http://localhost:8080/`.
5. The response `{access_token, refresh_token, expires_in}` is saved to `.secrets/tokens.json`.

## Daily refresh
`POST /authentication/v2/token` with `grant_type=refresh_token&refresh_token=…&scope=<same or subset>`.

| Token | Lifetime |
|---|---|
| Authorization code | 5 minutes |
| Access token | 60 minutes |
| Refresh token | 15 days. **Treat as single-use: always store the new one** |

The client (`aps_client.py`) also forces one refresh and a retry if any call returns 401.

## Permissions — who sees what
- A 3-legged token acts **as the signed-in user**. Forma applies that user's project membership and the tool permissions for Issues, Assets, Forms and Files.
- So the dashboard shows exactly what that user can see in Forma. If a relationship points to an issue the user can't see, the dashboard shows "not visible to you" (warning), instead of hiding it silently.
- Pick the account that runs the daily job on purpose: a project admin sees everything, a subcontractor account sees only their own items.
- The output HTML contains project data. Share it only in an access-controlled location.
- `python fomo1.py check` → "Issue permissions (users/me)" shows the current user's Issues permissions.

## Security checklist
- [ ] `.env` and `.secrets/` are in `.gitignore` and never uploaded to Claude, Teams or email.
- [ ] Upload `.env.example` (placeholders) to the Claude Project, **never** `.env`.
- [ ] Credentials were shared in a meeting/chat → **regenerate the client secret** in the APS portal once setup works, then update `.env`.
- [ ] Least-privilege scopes (`data:read`) until phase 2.

## Troubleshooting
| Symptom | Likely cause / fix |
|---|---|
| `redirect_uri mismatch` / `AUTH-001` on sign-in | Callback URL in `.env` ≠ APS app setting (check the trailing slash and `localhost` vs `127.0.0.1`). |
| Browser shows "can't reach localhost:8080" | Script isn't running, or port 8080 is in use. Close the other app or change the port in both the APS app and `.env`. |
| 401 on every call | Token expired and refresh failed → `python fomo1.py login`. |
| 403 on Forma APIs, hubs work | Custom integration not activated for this account, or the user isn't a member of the project / lacks tool access. |
| 404 on a project | Wrong ID format: Data Management needs `b.<uuid>`; Issues/Assets/Forms/Relationships need the bare `<uuid>`. |
| Empty issues in EMEA/AUS projects | Set `FORMA_REGION`. |


## Corporate networks
The app has no third-party dependencies (`simplehttp.py` wraps `urllib`) so it works behind HTTPS-inspecting proxies that break `pip`. See troubleshooting.md.
