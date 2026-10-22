# 03. Authentication (APS, 3-legged OAuth v2)

## What we have

- APS app with client ID and secret (in `.env`)
- Callback URL `http://localhost:8080/`. It must match the APS app settings **exactly**, including the trailing slash.
- Custom integration already enabled in Forma Account Admin for this client ID.

## Flow

1. **Login (once, interactive):** `py src/auth.py login`
   - Starts a tiny local HTTP listener on port 8080.
   - Opens the browser at:
     `GET https://developer.api.autodesk.com/authentication/v2/authorize?response_type=code&client_id=<id>&redirect_uri=http://localhost:8080/&scope=data:read`
   - User signs in with their Autodesk account. Browser is redirected to `http://localhost:8080/?code=...`.
2. **Exchange code for tokens:**
   `POST https://developer.api.autodesk.com/authentication/v2/token`
   - Header `Authorization: Basic base64(client_id:client_secret)`
   - Body (form-encoded): `grant_type=authorization_code`, `code`, `redirect_uri`
   - Returns `access_token` (about 1 hour), `refresh_token`.
3. **Daily refresh (unattended):** same token endpoint with `grant_type=refresh_token`, `refresh_token`, `scope=data:read`.
   - The refresh token is **single use**. Save the new one from every response immediately, before any other call.
   - Refresh tokens expire if unused for about 15 days *(VERIFY on current APS docs)*. A daily job keeps it alive. After a long break (holidays, PC off), run `login` again.
4. **Who am I:** `GET https://api.userprofile.autodesk.com/userinfo` with the access token. Log the user's name and email at the start of each run so it is clear whose permissions the data reflects.

## Scopes

- Phase 1: `data:read` (covers Data Management, Assets, Relationships, Issues and Forms reads) *(VERIFY per endpoint in docs)*.
- Phase 2: add `data:write` for creating issues. Requires a new login.

## Token storage

- `.tokens/token.json`, git-ignored, readable only by the Windows user.
- Contents: refresh token, access token, expiry time. Never logged or printed.

## Open point: unattended vs. personal login

3-legged means the dashboard reflects one person's permissions and depends on their refresh token. Alternatives (a 2-legged token with a service account) are possible for some APIs, but Forms is, as far as we know, 3-legged only *(VERIFY)*, and 2-legged would bypass per-user permissions. Decision logged in `08-decisions-and-open-questions.md`.
