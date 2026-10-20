# Security policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Report them
privately through
[GitHub security advisories](https://github.com/AnnusShahzad/Accura/security/advisories/new)
instead.

Include what an attacker can do, the steps to reproduce, and the version
or commit you tested. You'll get a reply within a few days, and a fix will
be released before the details are made public.

## Scope

Security-relevant areas include authentication and JWT handling,
encryption of stored API keys, guest-account isolation and expiry, the
SSRF guard on user-supplied URLs (MCP servers, custom endpoints,
webhooks), and the Stripe webhook signature check.

## Running a public instance

For an instance strangers can reach, keep the defaults from
[`render.yaml`](render.yaml): registration closed, `ALLOW_PRIVATE_URLS=false`,
and generated `JWT_SECRET` / `ENCRYPTION_KEY`. See
[`DEPLOYMENT.md`](DEPLOYMENT.md).
