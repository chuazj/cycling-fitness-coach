# Whoop Integration Plan

**Status:** Pre-build — execute when Whoop band arrives.
**Drafted:** 2026-05-10
**Author context:** Decision made jointly with Claude after evaluating (a) splitting the intervals.icu integration into its own skill, (b) building a standalone whoop-api skill, and (c) integrating Whoop as in-skill modules. Option (c) won.

---

## 1. Headline decisions

| Question | Decision | Reason |
|---|---|---|
| Standalone whoop-api skill? | **No** — modules inside `cycling-fitness-coach`. | Coaching value (Strain↔TSS reconciliation, Recovery-gated workout decisions) only lands when co-located with cycling logic. Standalone skill creates trigger contention, awkward skill-to-skill calls, and doubles install-path/sync overhead. |
| Refactor `intervals_icu_api.py` first as setup work? | **No.** | Refactor without driver. Original "Option B" split was rejected as speculative. |
| Build the multi-source readiness layer as part of Whoop integration? | **Yes.** | Earned by Whoop's arrival as a concrete second wellness source. Yellow/Red Flag rules need to apply to both sources → factor out. |
| Full V2 endpoint coverage from day one? | **Yes.** | Surface is only 12 V2 endpoints (excluding the V1→V2 mapping endpoint); phasing overhead — two release cycles, two doc passes, two test passes — exceeds the risk-mitigation benefit on an API this small. Within the single build, workflow wiring still prioritizes the high-value path (Recovery + Sleep + Workout) so the first end-to-end demo lands on day-one work, but every endpoint gets client-side coverage from the start. |

## 2. Pre-build verification (do all 3 before committing to build)

Three independent checks. Run them in any order; the build/no-build decision combines all three.

### Step 1 — Empirical data path check

Once the band arrives and is connected to your Whoop account:

1. Connect Whoop in intervals.icu's external integrations panel (if option exists), OR connect Whoop → Garmin Connect → intervals.icu chain.
2. Wait 24–48 hours for data to flow.
3. Run:
   ```bash
   python scripts/intervals_icu_api.py --wellness 7 -o wellness.json
   ```
4. Inspect `wellness.json`. Look for: HRV, RHR, sleep duration, sleep score, **Whoop Recovery score**, **Whoop Strain**.

**Decision rule:**
- If HRV/RHR/sleep flow but Recovery and Strain do not → build is justified (this is the expected outcome).
- If Recovery and Strain flow through → don't build native integration; `--wellness` already covers it.
- If nothing flows → confirm Whoop sync chain works at all before deciding.

### Step 2 — Whoop developer dashboard registration

Independent of band arrival; can do now.

1. Register at `https://developer-dashboard.whoop.com`.
2. Create OAuth app. Note client_id and client_secret (never commit these).
3. Verify:
   - Approval requirement (any waitlist or manual review)
   - Pricing tier — confirm personal/free tier covers the 13 V2 endpoints
   - Rate limits — make a probe request and inspect response headers (`X-RateLimit-*`)
   - Webhook availability vs polling-only
4. Pick a redirect URI strategy (see §6 — `http://localhost` is likely blocked).

### Step 3 — Decision

Combine Step 1 (data gap) × Step 2 (access cost):

| Step 1 outcome | Step 2 outcome | Action |
|---|---|---|
| Recovery + Strain missing from intervals.icu | Free tier covers needed endpoints | **Build full integration** as scoped here |
| Recovery + Strain missing | Free tier insufficient or approval blocked | Reassess — limited fetch via cheaper means (CSV export from Whoop?) or skip |
| Recovery + Strain flow through intervals.icu | — | **Don't build.** Use `--wellness`. |

## 3. Build scope — full V2 coverage in one cycle

All 12 V2 endpoints get client-side coverage in `whoop_client.py` in a single build. Within that build, workflow wiring still prioritizes the high-value path (Recovery + Sleep + Workout) — that's where the first end-to-end demo runs — but every endpoint is covered from the start.

**Endpoints wired into `whoop_client.py`:**

Coaching-active path (also drives workflow updates in this build):
- `GET /v2/recovery` (collection) + `GET /v2/cycle/{id}/recovery`
- `GET /v2/activity/sleep` (collection) + `GET /v2/activity/sleep/{id}`
- `GET /v2/activity/workout` (collection) + `GET /v2/activity/workout/{id}`
- `GET /v2/cycle` (index — wraps daily window)

Coverage path (client-side only at first; workflows pull these in lazily as needs arise):
- `GET /v2/user/profile/basic`
- `GET /v2/user/measurement/body` — replaces athlete-profile weight pull when Whoop is connected
- `GET /v2/cycle/{cycleId}/sleep`
- `DELETE /v2/user/access` — revocation handler

**Workflows wired in this build:**
- Mid-Week Check-In consumes Whoop Recovery in addition to intervals.icu wellness
- Weekly Review consumes Strain↔TSS reconciliation
- New: morning readiness gate (Recovery <30 → modify today's prescription)
- Athlete-profile weight pull falls back to Whoop body measurement when intervals.icu weight is missing

**Skipped:**
- `GET /v1/activity-mapping/{v1Id}` — V1→V2 migration only; greenfield V2 doesn't need it.

## 4. Architecture — final shape after build

```
scripts/
  whoop_oauth.py             ← NEW Phase 1: OAuth dance + token persistence (~150 LOC)
  whoop_client.py            ← NEW Phase 1: Whoop V2 HTTP wrapper (~200 LOC)
  whoop_api.py               ← NEW Phase 1: CLI orchestrator (~250 LOC)
  readiness.py               ← NEW Phase 1: Source-agnostic readiness (~150 LOC)
  intervals_icu_client.py    ← Extracted Phase 1 cleanup: HTTP + wire parsing (~150 LOC)
  cycling_metrics.py         ← Extracted Phase 1 cleanup: pure cycling math (~450 LOC)
  intervals_icu_api.py       ← Slimmed to CLI orchestrator (~600 LOC, down from 1,195)
  pmc_calculator.py          ← Imports updated; logic unchanged
  rpe_trend.py               ← Unchanged
  sparkline.py               ← Unchanged
  generate_zwo.py            ← Unchanged
  batch_generate_zwo.py      ← Unchanged
```

**Module dependency rule (enforce strictly):**
- `whoop_client.py` and `intervals_icu_client.py` MUST NOT import each other or `cycling_metrics.py`.
- `cycling_metrics.py` MUST NOT import either client.
- `readiness.py` MUST NOT import either client; takes normalized records as input.
- `whoop_api.py` and `intervals_icu_api.py` (the CLI orchestrators) are the only modules that compose client + metrics + readiness.

This rule is what makes the layering pay off — without it, the modules become a fake split.

## 5. Build sequencing — Whoop-first, refactor opportunistically

This sequencing inverts the original "Option B refactor first" plan. Whoop drives; intervals.icu cleanup falls out of it.

| # | Step | Validation gate |
|---|---|---|
| 1 | Build `whoop_oauth.py` — auth flow + token persistence + rotating refresh | Standalone CLI smoke: kick off auth, capture code, exchange, refresh once, verify new refresh token persisted |
| 2 | Build `whoop_client.py` — all 12 V2 endpoints (coaching-active + coverage) | Mocked-response unit tests for every endpoint; one live smoke per coaching-active endpoint, one batched smoke for coverage endpoints |
| 3 | Build `whoop_api.py` CLI — `--recovery N`, `--sleep N`, `--strain N`, `--summary N`, `--profile`, `--body` | Live smoke; output JSON validated against scope |
| 4 | Build `readiness.py` taking Whoop-shaped input only | Unit tests on Yellow/Red flag rules with Whoop input |
| 5 | Backport intervals.icu wellness through `readiness.py` — extract from `wellness_summary()`, normalize input shape | Existing `wellness_summary` tests still green; outputs identical |
| 6 | Opportunistic cleanup: extract `intervals_icu_client.py` and `cycling_metrics.py` from `intervals_icu_api.py` | Full `unittest discover` green; CLI smoke `--list-recent 3`; **patch strings** in `tests/test_with_mocks.py` re-targeted to new module |
| 7 | Wire workflows: Mid-Week Check-In, Weekly Review (Strain↔TSS), morning-readiness gate, athlete-profile weight fallback to Whoop body measurement | Manual end-to-end run with real data |

Each step is a separate commit. Step 5 is the architectural pay-off; step 6 is a 2-hour cleanup, not a 7-commit refactor.

## 6. OAuth setup — pinned facts (verified from developer.whoop.com 2026-05-10)

| Property | Value |
|---|---|
| Flow | Authorization Code |
| Auth URL | `https://api.prod.whoop.com/oauth/oauth2/auth` |
| Token URL | `https://api.prod.whoop.com/oauth/oauth2/token` |
| Required scopes | `read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement offline` |
| Access token TTL | 3600 seconds (1 hour) — short |
| Refresh token | Single-use, **rotating** — must persist new refresh token after each refresh, otherwise next refresh fails |
| Redirect URI | `https://...` or custom scheme `whoop://...`. **`http://localhost` not mentioned in docs — likely blocked.** |
| OpenAPI spec (canonical) | `https://api.prod.whoop.com/developer/doc/openapi.json` |

**Redirect URI strategy — localhost-first** (corroborated by third-party evidence on 2026-05-10; see §11 References):

The Whoop OAuth docs only show `https://...` and `whoop://...` *as examples*, but multiple working Whoop integrations register `http://localhost:N/callback` and use a one-shot local HTTP server to capture the auth code. This is the standard OAuth dev pattern and is far simpler than manual code copy.

| Option | Pros | Cons | Status |
|---|---|---|---|
| **Recommended: `http://localhost:8787/callback`** — spin up a one-shot HTTP listener on port 8787 during auth, capture `?code=...` from the redirect, shut down | One-click flow; no OS-level changes; standard OAuth dev pattern; supported by multiple working Whoop integrations | Port 8787 must be free during the initial auth grant (not a runtime concern after tokens are persisted) | **Use this** — verify acceptance during Step 2 dev-app registration |
| Fallback: manual code copy via `https://example.com/callback` | No local server needed | One-time paste per re-auth | Use only if Whoop dashboard rejects localhost registration |
| Custom scheme `whoop://callback` + Windows URL handler registration | One-click after setup | Windows-only; registry edits required | Not recommended — most friction |

**Research log — redirect URI verification (2026-05-10)**

This table records the sources consulted and what each says about whether `http://localhost:N/callback` is a valid Whoop OAuth redirect URI. Reproduce by re-fetching the URLs in §11 References.

| # | Source | Authority | What it says about redirect URIs |
|---|---|---|---|
| 1 | Whoop OAuth official docs (`developer.whoop.com/docs/developing/oauth/`) | First-party | Examples shown: `https://whoop.com/example/redirect`, `whoop://example/redirect`. Explicitly states *"You may provide multiple Redirect URIs that your client needs"* and *"The redirect URI on your OAuth authorization request must match the value in the Developer Dashboard."* **No mention of localhost — neither permitting nor forbidding it.** Examples are illustrative, not normative. |
| 2 | Whoop Postman tutorial (official) | First-party | Uses Postman's "Authorize using browser" feature; no concrete redirect URI cited. By offering an HTTP-protocol-agnostic flow, confirms dashboard validation isn't schema-locked to `https`/`whoop` only. |
| 3 | Whoop Passport tutorial (official, Node.js Express) | First-party | Uses `callbackURL: process.env.CALLBACK_URL` placeholder. No concrete URI; no constraint mentioned. |
| 4 | `NathanielDaniels/whoop-mcp-server` MCP server | Third-party, production-grade | **Registered redirect URI: `http://localhost:8787/callback`** (the URI cited in the source the user found). Spins up a temporary HTTP listener on `localhost:8787` during auth; persists tokens to `~/.whoop-mcp/tokens.json` (chmod 600). |
| 5 | Open Wearables documentation | Third-party | Local dev example uses **`http://localhost:8000/api/v1/oauth/whoop/callback`** — different port, same pattern. Demonstrates localhost works at multiple ports, not a single hardcoded value. |

**Verdict:** `http://localhost:N/callback` is accepted by Whoop's Developer Dashboard validation in practice. The official docs' `https://`/`whoop://` examples are illustrative, not exhaustive — and the docs' explicit "multiple Redirect URIs" language plus the absence of any "https-only" or "no-localhost" prohibition supports the third-party empirical evidence. Two independent third-party implementations corroborate.

**Confidence level:** High but not first-party verified. This user has not yet registered a Whoop dev app. The verification gate in the strategy table above (attempt to register `http://localhost:8787/callback` during pre-build Step 2 — see §2) is the final check before committing to this approach. If the dashboard rejects the URI, fall back to manual code copy and document the rejection error in the build log; the rest of the plan is unaffected.

**What was NOT verified by this research log:**
- Port-range restrictions (does Whoop allow any port, or only well-known ones?). Both 8000 and 8787 work in third-party examples; this user can pick freely.
- Whether multiple localhost URIs at different ports can be registered simultaneously on a single app (relevant if running parallel dev environments).
- Whether token-grant validation re-checks the URI scheme/host beyond exact-match against the registered URI.

These are second-order questions that don't block the build; resolve only if the build hits a wall.

**Verification gate** (run during §2 Step 2 — dev app registration): attempt to register `http://localhost:8787/callback` as a redirect URI in the Whoop Developer Dashboard. If accepted → proceed with localhost strategy. If rejected with a validation error → fall back to manual code copy and document the rejection message in the build log.

**Implementation sketch for the localhost flow** (for `whoop_oauth.py`):

```python
# Pseudocode
1. Generate state token (CSRF protection).
2. Open browser to: AUTH_URL + ?response_type=code&client_id=...&redirect_uri=http://localhost:8787/callback&scope=...&state=...
3. Start a stdlib http.server on 127.0.0.1:8787 in a thread.
4. Server's request handler: parse ?code= and ?state= from path, validate state, write code to a queue, respond to browser with "You can close this tab."
5. Main thread blocks on queue.get(timeout=120).
6. POST to TOKEN_URL with grant_type=authorization_code, code, client_id, client_secret, redirect_uri.
7. Persist {access_token, refresh_token, expires_at} atomically to ~/.whoop_tokens.json (chmod 600 on POSIX; Windows ACL note in setup doc).
8. Shut down listener.
```

## 7. Critical unknowns to resolve at build time

These were not specified in the developer.whoop.com pages I read on 2026-05-10. Resolve before building any module that depends on them:

| Unknown | Where it shows up in the build | How to resolve |
|---|---|---|
| Rate limits | `whoop_client.py` retry logic; `whoop_api.py --summary` polling cadence | Probe headers on first request; check developer dashboard or contact support |
| Pricing tier limits | All of build | Visible after dashboard registration |
| Data freshness window | Morning readiness flow timing | Empirical — log timestamps over a week |
| Webhook details | If present, replaces polling for daily updates | Read `/docs/developing/webhooks` (not yet read) |
| Refresh token lifetime | Token persistence design | Empirical — let one refresh sit for a week, see if next refresh works |
| Concurrent token use | Whether multiple devices/sessions can hold valid tokens | Test before relying on it |

## 8. Touchpoints in existing files

What gets edited (light touch in most cases):

| File | Change |
|---|---|
| `SKILL.md` | Add Whoop section in Setup; add `whoop_api.py` to Scripts inventory; add Whoop-related triggers to dispatch table; add `references/whoop_integration.md` to reference files table |
| `CLAUDE.md` | Add Whoop scripts to Architecture section; add OAuth section to Running Scripts |
| `README.md` | Add Whoop integration paragraph + setup snippet |
| `workflows/advise.md` (Mid-Week Check-In) | Consume Whoop Recovery alongside intervals.icu wellness via `readiness.py` |
| `workflows/plan.md` (Weekly Review) | Add Strain↔TSS reconciliation step |
| `workflows/analyze.md` | Optional: post-ride Strain comparison |
| `references/training_zones.md` (Yellow/Red Flag rules) | Update rules to reference Recovery score thresholds (e.g., Recovery <33 = Red, 34–66 = Yellow) |
| `references/setup.md` | Add Whoop OAuth setup steps |
| `references/whoop_integration.md` | NEW — auth setup, full V2 endpoint reference (all 12 endpoints), data shapes |
| `.env` template | Add `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_REFRESH_TOKEN_PATH` |
| `.gitignore` | Add `whoop_tokens.json` (or chosen token file path) |

## 9. Risks and watch-outs

| Risk | Mitigation |
|---|---|
| Whoop API approval gates build | Resolve in Step 2 before any code |
| Single-use refresh-token rotation: if a refresh response is lost mid-write, next refresh fails | Atomic token-file write (write to temp, rename); on auth failure, fall back to full re-auth flow with clear error message |
| OAuth dance breaks on Windows due to redirect URI quirks | Use manual code copy; document explicit steps |
| `readiness.py` abstraction leaks Whoop-shape into intervals.icu callers | Build with Whoop input first; backport intervals.icu second; tests for both shapes |
| Coaching workflows accidentally double-count: same recovery signal coming from both intervals.icu (via Garmin) and Whoop direct | Source-of-truth precedence rule — Whoop direct wins when both available; document in `readiness.py` |
| Strain↔TSS reconciliation invents conclusions | Both metrics measure load on different scales (Strain 0–21 logarithmic, TSS linear). Document the comparison as descriptive (delta direction) not normative (absolute equivalence). Calibrate per-athlete over weeks. |
| Build time creep — "while we're here" cleanup of unrelated code | Strict scope: each commit references this plan's step number |

## 10. The decision tree if step 1 reverses expectations

If empirical Step 1 shows Whoop Recovery and Strain *do* flow through intervals.icu's `--wellness` (unlikely but possible — sync chains evolve):

- **Do not build native Whoop integration.** Use `--wellness` data.
- Original "Option B" intervals.icu refactor remains rejected (no driver).
- Add Whoop-specific interpretation logic to `wellness_summary()` directly (small change).
- Revisit only if Whoop launches a feature that intervals.icu doesn't surface (e.g., Sleep stages, Strain components).

This branch is documented so future-you doesn't fall into a sunk-cost build.

## 11. References

| Resource | URL / location |
|---|---|
| Whoop API overview | https://developer.whoop.com/api/ |
| Whoop OAuth guide | https://developer.whoop.com/docs/developing/oauth/ |
| Whoop developer dashboard | https://developer-dashboard.whoop.com |
| Whoop OpenAPI spec | https://api.prod.whoop.com/developer/doc/openapi.json |
| Whoop Postman tutorial (official) | https://developer.whoop.com/docs/tutorials/access-token-postman/ |
| Whoop Passport tutorial (official, Node.js Express) | https://developer.whoop.com/docs/tutorials/access-token-passport/ |
| `NathanielDaniels/whoop-mcp-server` (third-party, uses `http://localhost:8787/callback`) | https://github.com/NathanielDaniels/whoop-mcp-server |
| lobehub MCP listing for the above (where the localhost redirect URI was first cited) | https://lobehub.com/mcp/nathanieldaniels-whoop-mcp-server |
| Open Wearables Whoop API integration docs (uses `http://localhost:8000/...` for dev) | https://openwearables.io/docs/providers/whoop-api-integration |
| intervals.icu wellness endpoint reference | `references/intervals_icu_api.md` (in this repo) |
| Yellow/Red Flag rules (current source of truth) | `references/training_zones.md` (in this repo) |
| Readiness logic (current implementation) | `wellness_summary()` in `scripts/intervals_icu_api.py` lines 806–940 |

---

**Trigger to act on this plan:** Whoop band arrival + 48 hours of data flowing. Run Step 1 first.
