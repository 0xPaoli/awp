---
name: mine-validator-stability
description: >
  Overlay skill for reproducing a healthy Mine Worknet validator setup on a
  new machine after the official mine-worknet skill is installed. Use when you
  need to patch the official validator runtime with the known-good stability
  fixes, force the safer gateway LLM route, isolate multiple validator wallets,
  roll validators out sequentially, or diagnose why validators look online
  locally but do not stay healthy on the platform.
---

# Mine Validator Stability

This skill does not replace the official `mine-worknet` skill. It is an
overlay for the parts that repeatedly broke in real validator operations.

Use it together with the official skill:

1. Keep using the official `mine-worknet` `scripts/run_tool.py` commands.
2. Apply the bundled stability patch from this skill.
3. Start validators with per-wallet isolation and `MINE_LLM_MODE=gateway`.
4. Roll out additional wallets one by one and watch for degradation.

## When To Use

Use this skill when the user wants any of these:

- reproduce a known-good validator setup on a fresh machine
- make Mine validators stay online and visible on the platform
- fix validator report failures caused by missing `assignment_id`
- avoid OpenClaw CLI noise polluting validator JSON scoring
- run many validator wallets without state/log collisions
- add validators slowly and verify that throughput does not get worse

## What This Skill Fixes

The bundled patch replaces three files inside the official `mine-worknet`
skill:

- `crawler/enrich/generative/openclaw_agent.py`
  Fixes noisy OpenClaw CLI output polluting JSON parsing.
- `scripts/ws_client.py`
  Makes WebSocket payload parsing tolerant to alternate field shapes.
- `scripts/validator_runtime.py`
  Fixes two real production problems:
  - WS tasks that arrive without `assignment_id` now fall back to HTTP claim.
  - HTTP heartbeat is sent every cycle, so validators stay visible online.

These were the practical failure points in real multi-wallet validator runs.

## Patch Workflow

After the official `mine-worknet` skill is installed, apply this skill's
patch before starting validators.

Run:

```powershell
python C:\Users\paoli\.codex\skills\mine-validator-stability\scripts\apply_validator_patch.py
```

Default target root is:

```text
C:\Users\<user>\.codex\skills\mine-worknet
```

If the official skill is installed elsewhere, pass `--target-root`.

Important:

- The patch script creates a timestamped backup inside the target skill root.
- The patch is tested against official `mine-worknet` `0.14.0`.
- If version differs, the script stops unless `--force` is passed.

## Single-Wallet Bring-Up

Use this order on a new machine:

1. Apply the patch.
2. Pick one validator wallet that already has on-chain validator eligibility.
3. Set isolated env vars for that wallet:

```powershell
$env:HOME=$env:USERPROFILE
$env:AWP_AGENT_ID='walletN'
$env:VALIDATOR_ID='validator-walletN'
$env:VALIDATOR_OUTPUT_ROOT='C:\Users\<user>\.codex\skills\mine-worknet\output\validator-runs-walletN'
$env:MINE_LLM_MODE='gateway'
```

4. Run the official doctor:

```powershell
python scripts/run_tool.py validator-doctor
```

5. Start the validator:

```powershell
python scripts/run_tool.py validator-start
```

6. Check status after roughly 1 minute:

```powershell
python scripts/run_tool.py validator-control status
```

Healthy startup means all of these:

- `state = running`
- `Eligible: yes`
- `Ready pool: joined`
- `WebSocket: connected`

Tasks may still be `0` for a short time. That is normal for validators.

## Multi-Wallet Isolation Rules

Never multi-open validators against the same defaults.

For every wallet, isolate all three:

- `AWP_AGENT_ID`
- `VALIDATOR_ID`
- `VALIDATOR_OUTPUT_ROOT`

Use `validator-runs-walletN` output roots. This prevents:

- status files overwriting each other
- logs mixing across wallets
- stop/status commands hitting the wrong wallet
- OpenClaw validator agents sharing the same identity

## LLM Routing Rule

For validators, prefer:

```text
MINE_LLM_MODE=gateway
```

Why:

- OpenClaw CLI can emit status lines into stdout
- long prompts can trigger command-length problems on Windows
- gateway mode was more stable in sustained runs

The patch still keeps the official routing stack available, but the operational
default for healthy validator fleets should be `gateway`.

## Rollout Strategy

When adding more validator wallets:

1. Record baseline `tasks_received`, `tasks_evaluated`, `errors`, and
   `last_action` for already-running wallets.
2. Start only one new wallet.
3. Watch roughly 3 minutes.
4. Only add the next wallet if:
   - the new wallet reaches `running / eligible / ready_pool / ws`
   - existing wallets continue to gain evaluations
   - there is no obvious new error spike

If throughput degrades, stop the newest wallet first and re-check.

## What To Trust

For validators, do not rely on profile `credit` as a real-time health signal.
In current runs it may be `null` even for healthy validators.

Use these instead:

- `tasks_received`
- `tasks_evaluated`
- `errors`
- `phase` and `phase_detail`
- `last_action`
- recent cooldown duration

Useful interpretation:

- low cooldown + steady evaluations = strong validator
- long cooldown + very few evaluations = weak / cold validator
- `502` or brief reconnects can be platform-side noise; look for recovery

## Platform Caveats

- The platform online list can lag behind local state by one or two heartbeat
  cycles.
- A validator can be healthy locally before the website reflects it.
- The patched heartbeat cadence is what prevents the "local running but not
  online on website" failure mode.

## Safety

- Never expose private keys or session tokens.
- Never export wallets as part of this setup.
- Use the official `run_tool.py` commands for start/stop/status.

