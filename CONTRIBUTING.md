# Contributing to Accura

Thanks for helping out. Bug reports, fixes, docs and features are all
welcome.

## Getting set up

```bash
npm install
npm run setup:backend
cp backend/.env.example backend/.env    # set JWT_SECRET and ENCRYPTION_KEY
npm run dev                             # API on :8000, web on :3000
```

No AI key is needed to run the tests. For trying the app by hand, any
OpenAI-compatible endpoint works (see [`DEPLOYMENT.md`](DEPLOYMENT.md#ai-provider)).

## Before opening a pull request

```bash
npm test                 # backend suite, SQLite, no network needed
npm run lint
npm run build
```

CI runs the same checks, plus the backend suite on PostgreSQL and a
Docker image build.

For UI changes, check the page in light and dark mode and at phone width.
[`tests/e2e/`](tests/e2e/) has Playwright scripts that drive the whole
app and audit every page for accessibility and layout problems.

## Commit messages

Write them the way the Linux kernel does: a short `area: imperative
summary` line, a blank line, then a body explaining **why** the change is
needed, wrapped at about 72 columns.

```
chat: keep the retry button after a provider timeout

A timeout marked the run failed before the error message was stored,
so the client stopped polling and never showed Retry. Store the
message first, then flip the status.
```

Keep each commit to one logical change, so it can be reviewed and
reverted on its own.

## Reporting bugs

Use the issue templates. Include how you run Accura and the relevant
log lines, with any API keys removed. Report security issues privately
instead (see [`SECURITY.md`](SECURITY.md)).
