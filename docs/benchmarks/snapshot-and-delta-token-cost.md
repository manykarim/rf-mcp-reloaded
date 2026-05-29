# Snapshot + Delta Token-Cost Benchmark

Generated: 2026-05-29T08:46:32.915629+00:00

Response sizes are measured in bytes of the JSON the tool returns to the agent. Tokens are approximated as `bytes / 4` (English + JSON heuristic).

## 1. Delta `rf_session(action='get')`

_polling loop, session unchanged, 10 polls._

| Mode | Mean bytes | Mean tokens (~) |
| --- | ---: | ---: |
| `action='get'` (full) | 309 | 77 |
| `action='get'` with `since_version` (unchanged) | 114 | 28 |
| **Savings** | **63.1%** | |

## 2. `app_inspect_state(snapshot_kind='dom')`

### single dom snapshot, ~8 KiB raw payload

| Mode | Bytes | Tokens (~) |
| --- | ---: | ---: |
| Default (`manifest` only) | 917 | 229 |
| `return_inline=True` (default cap) | 9,724 | 2,431 |
| `return_inline=True` (uncapped) | 9,724 | 2,431 |
| `summary_only=True` | 917 | 229 |
| **Manifest vs uncapped inline savings** | **90.6%** | |
| **summary_only vs uncapped inline savings** | **90.6%** | |

### single dom snapshot, ~128 KiB raw payload

| Mode | Bytes | Tokens (~) |
| --- | ---: | ---: |
| Default (`manifest` only) | 923 | 230 |
| `return_inline=True` (default cap) | 9,730 | 2,432 |
| `return_inline=True` (uncapped) | 141,942 | 35,485 |
| `summary_only=True` | 923 | 230 |
| **Manifest vs uncapped inline savings** | **99.3%** | |
| **summary_only vs uncapped inline savings** | **99.3%** | |

### single dom snapshot, ~512 KiB raw payload

| Mode | Bytes | Tokens (~) |
| --- | ---: | ---: |
| Default (`manifest` only) | 924 | 231 |
| `return_inline=True` (default cap) | 9,731 | 2,432 |
| `return_inline=True` (uncapped) | 565,024 | 141,256 |
| `summary_only=True` | 924 | 231 |
| **Manifest vs uncapped inline savings** | **99.8%** | |
| **summary_only vs uncapped inline savings** | **99.8%** | |

## Takeaways

- File-first defaults turn a multi-kilobyte DOM into a sub-kilobyte response. Agents read the file only when the summary doesn't suffice.
- `since_version` collapses repeated session polls to a near-empty payload — the largest predictable win in tight authoring loops.
- `summary_only=True` is the cheapest knob (sub-300 bytes) when an agent just wants to know `did the page change?` between steps.
