---
name: authn-authz-review
description: Review authentication, session management, and authorization as one system while keeping the two questions apart — who the caller is proved at the boundary, and what they may do to this object checked per request — using slow salted password hashing, constant-time comparison, single-use tokens, default-deny authorization, server-side object and tenant scoping, allowlisted field binding, and CSRF protection; Use when adding or reviewing login, session, token, password reset, MFA, role or permission changes, impersonation, multi-tenant queries, admin routes, exports, webhooks, or any endpoint whose authorization is inferred from the caller merely being logged in.
metadata:
  owner: Michal
  domain: security
---

# AuthN & AuthZ Review

## When to use
- Login, session, token, password reset, email change, MFA, recovery codes, or logout paths.
- A new route, handler, job, webhook, export, resolver, or admin path — anywhere a decision "may they?" is made.
- Role or permission changes, impersonation, multi-tenant scoping, or a request that binds a client-supplied object.

## Rules

**Keep the two questions apart, and make the code do the same.**
- **Authentication answers WHO** — proved at the boundary from a credential the client cannot forge.
- **Authorization answers WHAT MAY THEY DO TO THIS OBJECT** — checked per request, per object, per action.
- Inferring authorization from authentication is itself a finding.

**Authentication checks**
- Credentials stored with a slow, salted, adaptive password hash, compared in constant time. *(Examples of the property: bcrypt, scrypt, Argon2, PBKDF2 with a tuned work factor.)* Never a fast hash, never unsalted, never reversible or "encrypted".
- Identical response **and** comparable timing for unknown user vs wrong password — otherwise the endpoint enumerates accounts.
- Bounded backoff or lockout that cannot be weaponised into a permanent denial of service against a victim account.
- Reset and email-change tokens: single-use, short-lived, unguessable, and invalidating prior sessions.
- MFA on every risky path, with single-use, hashed, regenerable recovery codes.
- No session fixation: the identifier is regenerated on any privilege change.
- Explicit token and session lifetime, rotation, and server-side revocation that **actually takes effect** at the store, not just in the client.
- Tokens never in URLs, referrers, or logs.

**Token-specific traps**
- The accepted algorithm is pinned by allowlist and never read from the token.
- Algorithm confusion and acceptance of an unsigned token are impossible by construction, not by a later check.
- A caller-supplied key id cannot select an attacker-controlled key.
- The signature is verified **before** any claim is read.
- Issuer, audience, subject, and required claims are validated — not merely decoded; expiry and not-before are checked; revocation is enforced for tokens that must die early.

**Authorization checks most often missed**
- Enforced on **every** path, not only the UI: direct API calls, alternate verbs, bulk and export endpoints, resolvers, webhooks, background jobs, admin and internal routes.
- **Object-level:** can user A fetch user B's object by changing an identifier? Ownership is checked server-side per object, never implied by the route shape.
- **Function-level:** including destructive and administrative actions.
- **Multi-tenancy:** every query is scoped by tenant — *including* jobs, exports, caches, and admin paths — with the tenant id taken from the authenticated context, never from a request body, query parameter, or client-set header.
- **Mass assignment / over-posting:** bind only allowlisted fields. A client-supplied role, tenant, owner, or price field is **rejected**, not quietly ignored.
- **CSRF:** any state-changing request reachable by an ambient cookie or session credential needs CSRF protection.

**Privilege-escalation paths, looked for explicitly:**
- Role and permission change endpoints; impersonation or "act as".
- Internal headers or claims trusted from a client — i.e. a proxy the attacker can address directly.
- Confused deputy: a service acting with more privilege than the end user is entitled to.
- Cached authorization decisions that outlive a revocation.

**Default-deny is the only safe default for a new endpoint** — including when the policy store, the cache, or the identity provider is unavailable. Fail closed (`correctness-errors`).

## Verify
- The unknown-user and wrong-password responses are compared for body, status, and timing on the same path.
- Each new route has a recorded authorization decision and its enforcement point (middleware, policy, or handler).
- Object-level checks are tested with user A requesting user B's identifier by direct call, not through the UI.
- Grep every query, job, export, and cache key for the tenant scope and confirm the tenant id's origin is the authenticated context.
- A request body containing role, tenant, owner, or price is rejected, not ignored.
- Revoking a session or role is observed to take effect on the next request, including from a warm cache.

## Anti-patterns
- Not "logged in, so allowed" — that is authentication doing authorization's job.
- Not an admin check on the UI route only.
- Not a tenant id read from a header, a body, or a query parameter.
- Not a denylist of forbidden fields on bind; an allowlist of permitted ones.
- Not a fast hash, a silent unknown-user response, or a lockout an attacker can trigger forever.
- Not trusting an unsigned, unverified, or wrong-audience token because it decodes cleanly.
