# DecisionMesh — Verification

## Live UI verification: 2026-11-06

Target: `http://127.0.0.1:5173/#/`, using the running development UI/API and the configured local `system` model. Browser: installed Google Chrome through Playwright. Desktop viewport: 1440 × 1000; mobile: 390 × 844. Source data and actions were limited to clearly labeled QA scenarios and a separate QA inventory entity. Local simulation was the only action adapter used.

### Verified flows

- All five navigation destinations and six editable scenario presets.
- Agent creation, editing, and removal through React dialogs.
- A real seven-role workflow: six assessments, a human checkpoint, saved operator suggestions, and final synthesis from the seventh role.
- History search and saved findings; analytics period selection, sorting, and agent outcome details.
- Inventory entity creation, incoming observations, versioned state, and four calculated candidate actions.
- Real Agno negotiation with peer exchange over two rounds: eight valid, evidence-linked proposals after the compatibility fix.
- Scoped approval, simulated execution, identical-request replay returning the same acknowledgment, and creation of an outcome reassessment.
- External event JSON entry, exact-event deduplication, stale-event rejection, inventory drift, and stale-approval rejection.
- Continuous demonstration feed start/stop and automatic state/decision creation.
- Saved case evidence in the workspace, policy-required human review, empty-rerun guidance validation, a feedback-driven linked rerun, page reload, history-based checkpoint recovery, and mobile finalization.
- A full six-scenario benchmark with 12 architecture trials, saved comparison cards, exact recorded model-call counts, and JSON export.
- Benchmark cancellation through the UI and retrieval of completed results after reload.
- No uncaught JavaScript errors or console errors in the final browser pass. Mobile pages fit the viewport; wide comparison tables scroll within their panels.

### Issues found and fixed

1. **Structured proposal compatibility.** The original Agno construction asked for Markdown while research prompts requested JSON. The local model also altered long source IDs. Proposal calls now disable Markdown and put the JSON contract in system instructions. Prompts supply compact evidence aliases, which are validated and resolved to the original source IDs before storage. Unsupported references remain rejected.
2. **Bounded format repair.** An invalid proposal receives at most one explicit repair request. Both architectures use the same collection/validation path. Raw invalid output and repair requests remain in the trace; repair calls count toward recorded cost/latency. Provider failures and unrepaired outputs remain visible and can force review.
3. **Missing browser icon.** Added a local SVG icon and entry-document reference to remove the browser's favicon 404.
4. **Inventory selection race and stale details.** A late default-selection effect could overwrite a user choosing another twin immediately after navigation. Initialization now uses the current state value, and entity/case/job details render only when their IDs match the current selection. The saved live suite explicitly waits for the selected case so an unrelated twin cannot satisfy its assertions.

The saved `npm run test:live` command subsequently passed all 14 core checks in a fresh run. The selection fix also passed 12 immediate page-load switches between two persisted QA entities. Cancellation and the feedback/rerun/reload flow were checked in the separate live pass described above.

During test development, selectors were corrected to use the actual agent-performance heading and to scope dropdown queries to combobox roles. Those were harness corrections rather than application failures.

### Recorded benchmark snapshot

One repetition per scenario; six samples per architecture. These are measured outputs from the configured model, not seeded fixture scores.

| Metric | Centralized | Orchestrated |
| --- | ---: | ---: |
| Samples | 6 | 6 |
| Mean synthetic quality / 100 | 50.00 | 95.44 |
| Optimal-choice rate | 50.00% | 83.33% |
| Policy compliance | 50.00% | 100.00% |
| Model calls, including format repairs | 6 | 45 |
| Mean machine-phase time | 1.562 s | 14.664 s |
| Trials with provider/unrepaired-format failures | 16.67% | 33.33% |

Provider failures and rejected/budget-violating choices were retained. The orchestrated variant includes deterministic policy/arbitration and a larger call budget. This small synthetic comparison does not isolate the benefit of agent reasoning or establish enterprise-scale decision quality. Machine/server pauses and inter-trial scheduling also prevent interpreting total experiment wall time as throughput. See [EnterpriseLoop.md](EnterpriseLoop.md) for the oracle, rubric, timing, and unmeasured metrics.

A second complete 12-trial run, executed by the saved suite after the selection fix, scored centralized **50.00** and orchestrated **73.68**, using **6** and **38** model calls respectively. Orchestrated policy compliance remained 100%; partial provider failures remained visible. The variation between runs is material and reinforces the limited scope of these measurements. Total completed live benchmark coverage: **24 trials across two runs**, plus a separately cancelled benchmark.

QA records remain in local history and Enterprise lab for inspection. The detailed report and screenshots are stored under `data/ui-tests/live-2026-11-06/`, excluded from Git. Subsequent scripted runs create their own timestamped output directories and QA records.

## Automated regression checks

- `poetry run python -m unittest discover -s backend/tests -v`: **50 passing tests**. Includes isolated enterprise state/receipt transactions, deduplication/order/freshness, hard budget rules, approvals/expiry, idempotency, drift reconciliation, peer exchange, invalid output/repair, accurate repair-call accounting, cancellation, stale negotiation, restart recovery, fixture evaluation, and the real Agno adapter with mocked HTTP.
- `npm --prefix frontend test`: **5 passing protocol/format tests**.
- `npm --prefix frontend run build`: TypeScript and Vite production build pass.

The deterministic backend fixture suite and real-model browser runs are separate evidence. Backend restart recovery is covered with isolated databases; the user's running backend was not manually stopped for a destructive restart experiment. Windows and live Ollama integration were not exercised in this pass.

## Rerun the live browser checks

Start the API, Vite server, and configured model server first. From the project root:

```bash
npm --prefix frontend install
npm --prefix frontend run test:live
```

The saved Playwright suite defaults to `http://127.0.0.1:5173/#/` and installed Chrome. It uses real model calls, creates QA records, and leaves the servers running. Results/screenshots go to `data/ui-tests/<timestamp>/`. It expects the seven default agent roles and an available model; it does not reset the catalog or delete existing records.

Optional environment settings:

| Variable | Purpose |
| --- | --- |
| `DECISIONMESH_UI_URL` | Override the live UI address |
| `PLAYWRIGHT_CHANNEL` | Browser channel; default `chrome` |
| `PLAYWRIGHT_MODULE` | Optional path to an already-installed Playwright module |
| `LIVE_UI_OUTPUT_DIR` | Override the output directory |

For bundled Chromium, run `npx playwright install chromium` from `frontend/` and set `PLAYWRIGHT_CHANNEL=chromium`. Model behavior can change between runs; the suite checks lifecycle/persistence and feasible execution, while the benchmark records decision quality and failures rather than requiring every model choice to be optimal.
