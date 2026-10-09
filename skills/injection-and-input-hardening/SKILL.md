---
name: injection-and-input-hardening
description: Trace every untrusted source to every sink, including second-order flows, and hold each flow to the property that defeats its family — bound parameters instead of interpreter strings, encoding per sink context, containment after canonicalisation, allowlisted destinations re-validated after every redirect, data-only deserialization with limits, and size bounded before parsing; Use when adding or reviewing a query, shell command, template, file or archive path, outbound HTTP request, deserializer, regex, or parser that can be reached with input you did not create.
metadata:
  owner: Michal
  domain: security
---

# Injection & Input Hardening

## When to use
- Data you did not create reaches a query, command, template, path, deserializer, outbound request, regex, or log.
- A stored value written by a user is read back and used — that is still untrusted input.
- Adding a parser, a file handler, an archive extractor, or an outbound HTTP client.

## Rules

**Trace every source to every sink, including second-order flows.** Data that was user-supplied when written and is read back later is still untrusted: a taint label survives storage. Sanitising on write does not launder it. Follow the value across jobs, caches, exports, and re-imports. For each flow, name the family and the property that defeats it.

**Interpreter injection** (SQL, NoSQL, LDAP, command, template, header, log): the interpreter never receives attacker text **as structure**. Bind parameters; use the structured argument, document, or expression form the API offers. Never build an interpreter string by concatenation or interpolation. Filters, escaping functions, and denylists are not this control. *(Examples of the property: parameterised query APIs, argument-vector process spawn, auto-escaping template engines, structured log formatters.)*

**XSS and output encoding:** encode **per sink context** — HTML body, HTML attribute, URL, script, CSS — never once globally. Prefer an auto-escaping templating engine; keep unescaped output explicit, marked, and rare. Sanitisation is not encoding, and neither substitutes for the other.

**Path traversal and files:** the resolved path lies inside the base directory **after canonicalisation with symlinks resolved**. Verify containment once, centrally, in the path resolver — not at each call site. Close the TOCTOU window between check and open: open by descriptor, or re-check after open. For archives, reject members that are absolute, contain `../`, or resolve outside the destination, and rewrite member names rather than trusting them. Temp files are unpredictable and created exclusively.

**SSRF:** destinations come from an allowlist of hosts, ports, and schemes. Block loopback, link-local, and cloud metadata ranges. Resolve the name, validate the resulting address, and **re-validate after every redirect**; constrain redirect depth and targets. Never let a caller choose a scheme or host that reaches an internal zone.

**Deserialization:** untrusted input is parsed by a **data-only, schema-bound** format with size, depth, and element-count limits. A polymorphic or native deserializer that can instantiate types or invoke callbacks is never applied to untrusted input, whatever the language or framework.

**ReDoS and algorithmic complexity:** bound the input size **before** parsing. Prefer linear-time matching. Cap work amplification explicitly — per-item cost × item count, decompression ratio, page size.

**Parser and Unicode differentials:** compare after **one** explicit normalisation form. Treat homoglyphs, mixed case, invisible characters, and alternate or overlong encodings as distinct inputs. Canonicalise once at the boundary and forbid further normalisation downstream.

**The four properties, stated once:**
1. Validate and normalise at the boundary.
2. Canonicalise before comparing.
3. Bound size before parsing.
4. Reject when the type or shape is wrong.

Name libraries as *examples* of a property, never as the rule — a library name is a version away from being wrong.

## Verify
- Every sink has a named source, including the second-order ones reached from storage.
- Each interpreter sink uses a bound or structured form; grep the diff for concatenation into a query, command, or template.
- Path handling: test encoded, doubled, and symlinked traversal variants; containment is enforced in one shared resolver.
- The outbound client is tested against a redirect to an internal address and against a metadata-range host.
- Archive extraction is tested with an absolute member, a `../` member, and a symlink member.
- Oversized, deep, and pathological inputs are rejected *before* parsing, and the test asserts the rejection rather than the absence of a crash.

## Anti-patterns
- Not escaping at the sink instead of encoding for the context.
- Not sanitising on write and calling stored data trusted.
- Not a denylist of extensions, characters, or blocklisted hosts.
- Not a containment check at three call sites and none in the resolver.
- Not "the framework escapes it" without naming the context it escapes for.
- Not naming a library as the control instead of the property it provides.
