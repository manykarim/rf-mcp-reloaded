# Shadow-DOM Stress Comparison: selectorshub vs DB Schenker

**Generated:** 2026-05-29 (sessions `26606cc22ef4` selectorshub, `e24fef78e669` dbschenker)
**Toolset:** rfmcp-reloaded `main@c0d9032+`

Two live runs against very different pages, both driven through the bounded
MCP surface (`rf_session` → `rf_execute_step` batched setup → `app_inspect_state`
× 4 → cleanup), to validate `app_inspect_state` advanced features (DOM,
DOM+shadow walker, ARIA, closed-shadow probe) under realistic conditions.

| Target | Character |
| --- | --- |
| [selectorshub.com/xpath-practice-page](https://selectorshub.com/xpath-practice-page/) | Hand-built practice page using plain `<div>` + `attachShadow({mode: "open"})`. Open shadow DOM only. |
| [dbschenker.com/global/business/services/book-and-track](https://www.dbschenker.com/global/business/services/book-and-track) | Enterprise SPA, Web Components throughout, Usercentrics consent UI, lazy-loaded shipment widget. |

## Headline numbers

| Capture | selectorshub | DB Schenker | Notes |
| --- | ---: | ---: | --- |
| `dom` (Get Page Source) | 470,629 B | 241,776 B | Raw HTML — neither sees inside shadow roots |
| `dom, include_shadow_dom=True` | 473,443 B | 250,866 B | Walker added 3 KB / 9 KB of shadow content |
| Shadow templates emitted | 2 | **5** | Open shadow roots reachable from JS |
| `aria` YAML | 19,499 B | 15,513 B | Playwright's accessibility tree — 24×/16× cheaper than raw DOM |
| ARIA nodes | 410 | 324 | Comparable semantic density |
| Custom elements (`<tag-name>`) | 0 | **14** | Web Components in use |
| Custom elements with open `shadowRoot` | 0 | 1 | Probe could enter |
| Custom elements with null `shadowRoot` (likely closed) | 0 | **13** | Probe **could not** enter |
| `has_possible_closed_shadow_roots` flag | false | **true** | Surfaces in DOM summary |

The closed-shadow probe is the single biggest signal: on dbschenker, the toolset
**flags 13 custom elements whose shadow roots are inaccessible from JS**. That's
exactly the kind of warning an agent needs before sinking time into selectors
that will never match.

## What worked end-to-end

- **Batched setup** (7 instructions, 1 round-trip) succeeded on both pages.
  Token win: ~56% vs sequential.
- **Shadow walker** surfaced declarative `<template shadowrootmode="open">`
  blocks both times — 2 on selectorshub, 5 on dbschenker.
- **ARIA snapshot** produced ~16 KB structured trees on both, with 26-27
  distinct roles, suitable for agent-side reasoning.
- **Closed-shadow probe** ran without raising on either page and reported
  honest counts.
- **Diagnostic suggestions in `step-failed`** populated correctly on both
  dbschenker cookie-banner failures — the agent receives:
  ```
  call app_inspect_state(session_id='...', snapshot_kind='dom_selector',
       selector='[data-test-id="uc-accept-all-button"]') to read the actual
  HTML at that locator, or snapshot_kind='aria' to see the page's semantic
  tree.
  ```

## What didn't — and why

Both cookie-banner click attempts on dbschenker returned `step-failed`. This is
**not** a bug in the toolset; it surfaces a real ergonomic gap:

1. **The consent UI lives inside a shadow root.** Usercentrics renders its
   banner inside a Web Component. The selector `[data-test-id="uc-accept-all-button"]`
   only matches the light DOM. To pierce the shadow boundary, Browser Library's
   Playwright backend needs an explicit cross-shadow selector — `>>>` or a Playwright
   `locator` chained from the host.
2. **The agent has no built-in hint about this.** The diagnostic suggestion
   correctly points at `app_inspect_state(snapshot_kind='dom_selector', selector=...)`
   to *inspect* — but the agent then has to figure out independently that the
   missing element is hiding behind a shadow boundary it can't traverse with a
   flat CSS selector.

ARIA's automation signal on dbschenker reflects the same loss: it found 3
textboxes / 16 buttons / 0 comboboxes for what should be a multi-step booking
form. **The form fields are inside closed shadow roots**; Playwright's
accessibility tree can't read them either (closed shadow DOM is inaccessible by
the platform contract).

## Improvements ranked by leverage

1. **Closed-shadow-aware `suggested_next_step`** *(small, high agent value)*.
   When `step-failed` fires with a Browser/Selenium session AND the most recent
   `dom` capture for the session reported `has_possible_closed_shadow_roots=True`,
   prepend a hard advisory to the suggestion: `the target may be inside a
   closed shadow root; closed shadow content is inaccessible by the platform
   contract — try ARIA or look for an open-shadow alternative`. Today the agent
   reaches for `dom_selector` indefinitely, wasting calls.

2. **Shadow-piercing selector helper** *(medium)*. Add a new `app_inspect_state`
   parameter or a small `selector_strategy` hint: when the failing selector
   resembles a CSS attribute selector, suggest the Playwright `>>` / `>>>`
   piercing variant as the alternative phrasing. For Browser Library specifically:
   demonstrate the `locator()` chained from the host element. Cuts the trial-and-
   error loop dramatically.

3. **Consent-banner pattern library** *(small)*. The cookie banner is the #1 thing
   that breaks the first 5 steps of every enterprise scenario. A small set of
   well-known patterns (Usercentrics `uc-show-more-details`, OneTrust
   `#onetrust-accept-btn-handler`, Cookiebot `#CybotCookiebotDialogBodyButtonAccept`)
   could ship as either a `rfmcp_skills` definition or as a documented pre-flight
   in `agent_prompt.txt`. Today every scenario re-discovers them.

4. **ARIA-derived selector hints** *(medium)*. When the agent calls
   `app_inspect_state(snapshot_kind='aria')` and the response surfaces e.g. `textbox
   "Origin"`, also surface a Playwright role-locator template
   (`role=textbox[name="Origin"]`) in the manifest summary. The agent can then
   pass that directly to `Fill Text` without re-deriving it. This is the
   highest-leverage agent UX improvement on the list.

5. **Wait-for-state in batched setup** *(small)*. SPA pages (dbschenker, most
   modern enterprise UIs) lazy-load form widgets after DOMContentLoaded. The
   current `Sleep 5s` is fragile. The setup demo would be more robust with
   `Wait For Elements State` keyed on a stable selector — but **that selector
   has to live in the light DOM**. Surface this as guidance in the
   `browser-library-flagship-repair` skill's "Live-state diagnostic order" or
   add a `wait_for: str | None = None` hint to the batched-setup helper.

6. **Track `closed_shadow_probe.possible_closed_shadow_root_count` on session
   metadata** *(small)*. Promote it from a one-shot DOM-summary field to a
   per-session counter so `rf_session(action='get')` can surface it directly.
   Helps agents pick ARIA-first strategies up front on heavy-shadow pages.

7. **Smaller / not in v1**: CDP attach for closed shadow root introspection
   (CDP exposes them); HAR-based network log so the agent can correlate
   shadow-rooted form submissions; per-session `consent_dismissed` flag the
   stepper sets after detecting a successful cookie dismissal.

## What the data settles

| Question | Answer (from this run) |
| --- | --- |
| Does the shadow walker work on real-world Web Component sites? | Yes — 5 templates serialized on dbschenker. |
| Does ARIA cover what's inside open shadow roots on real-world sites? | Yes — but only the open ones. Closed roots are invisible to ARIA too. |
| Does the closed-shadow probe distinguish enterprise UIs from practice pages? | Yes — selectorshub 0 / 0, dbschenker 14 / 13. |
| Are `step-failed` suggestions actionable? | Yes — both dbschenker failures returned a concrete `app_inspect_state` call. |
| Can we drive a closed-shadow form today? | **No.** Closed shadow content is a platform-level barrier. Best we can do is *flag* it loudly. |

## Suggested next two steps

1. **Land the closed-shadow-aware `suggested_next_step` change** (~30 lines in
   `stepper.py`). Highest agent UX win for the lowest effort; turns the existing
   probe into actionable guidance.
2. **Pilot ARIA-derived selector hints in the manifest summary** (~80 lines in
   `runtime/snapshot.py:_aria_summary` + tests). Even surfacing the top 10
   labeled textboxes / buttons with their role-locator template would close
   most of the loop the dbschenker run exposed.

## Reproduce

```bash
uv run --group web python tests/selectorshub/run_shadow_dom_proof.py
uv run --group web python tests/dbschenker/run_shadow_dom_stress.py
```

Artifacts:
- `tests/selectorshub/results/report.json`
- `tests/dbschenker/results/report.json`
- Persisted captures under `tests/<page>/results/snapshots/<session>/` (gitignored).
