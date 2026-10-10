# =============================================================================
# opencode-harness — install agents & skills into the global opencode config
# =============================================================================
#
# Usage:
#   make                 # same as `make deploy` (deploy is the default target)
#   make check           # assert permission consistency; installs nothing
#   make deploy          # non-destructive install (overwrites same-named files)
#   make reinstall       # destructive: wipe agent/, skills/, opencode.json, then
#                        # a fresh deploy
#   make clean           # destructive: remove agent/, skills/, opencode.json only
#   make eval            # behavioural eval harness, default tier (== eval-static)
#   make eval-static     # tier 1: deterministic config-derived assertions
#   make eval-selftest   # prove the gates fail on seven seeded defects
#   make eval-behavior   # tier 2: real model calls; needs EVAL_CONFIRM=1
#   make help            # list targets
#
# `deploy` and `reinstall` both run `check` first and refuse to install a tree
# whose bash deny-list, permission ordering, or per-agent skill scope has drifted.
# The `eval*` targets also depend on `check`, and add assertions `check` does not
# make — see the eval section below and eval/README.md.
#
# Destination (overridable, e.g. for testing):
#   make DEST=/tmp/opencode-deploy-test deploy
#
# Installs into: $(HOME)/.config/opencode/  by default, i.e.
#   agent/*.md              -> $(DEST)/agent/
#   skills/*/SKILL.md       -> $(DEST)/skills/*/SKILL.md
#   opencode.json           -> $(DEST)/opencode.json
#
# WARNING: `reinstall` and `clean` delete inside $(DEST). They refuse to run
# unless $(DEST) looks like a real opencode config dir (see the safety guard
# below), so a typo like `make DEST= clean` cannot turn into `rm -rf /agent`.
# Never point those at $(HOME) itself.
# =============================================================================

# -----------------------------------------------------------------------------
# Default goal
# -----------------------------------------------------------------------------
# Stated explicitly, not left to position. GNU make takes the FIRST target in the
# file as the goal for a bare `make`, which makes the default a positional
# property: inserting any target above `deploy` silently changes what bare
# `make` does, with no diff to read and nothing to fail. `check` was inserted
# above `deploy` and did exactly that — the documented default quietly became
# "assert permissions, install nothing", and it still exited 0, because running
# the wrong goal legally is indistinguishable from running the right one.
#
# `.DEFAULT_GOAL` carries the intent instead, so reordering the file, adding a
# target, or moving a shared `define` block above the targets cannot re-break it.
# It only decides WHICH goal a bare `make` selects; every target that is named on
# the command line (`make check`, `make deploy`, `make reinstall`, `make eval*`)
# overrides it and is unaffected.
#
# The assertions are not bypassed by this. `deploy: check` means bare `make` now
# runs the same `CHECK_CMDS` gate it always did, first, and refuses to copy a
# drifting tree — see the comment on `deploy` below. `check` stays a target and
# stays the prerequisite of `deploy`, `reinstall` and `eval*`.
# -----------------------------------------------------------------------------
.DEFAULT_GOAL := deploy

SHELL := /bin/zsh

# Destination root. `?=` so `make DEST=/tmp/somewhere deploy` works. Note that
# `make DEST= ...` (explicitly empty) still overrides, hence the guard below.
DEST ?= $(HOME)/.config/opencode

# Source root (where this Makefile lives).
SRC := $(CURDIR)

# The three things we manage inside $(DEST).
#
# `agent/` and `skills/` match the directories opencode actually scans
# (Glob.scan("{agent,agents}/**/*.md") and "{skill,skills}/**/SKILL.md"), so the
# repo layout and the install layout are the same spelling. That keeps a skill
# loadable straight from the repo and from an install.
AGENTS_DEST := $(DEST)/agent
SKILLS_DEST := $(DEST)/skills
CONFIG_DEST := $(DEST)/opencode.json

# -----------------------------------------------------------------------------
# Safety guard
# -----------------------------------------------------------------------------
# REQUIRE_DEST: the minimum for any target — DEST must be set and must not be
# the filesystem root. Catches the empty-variable / typo cases.
#
# REQUIRE_OPENCODE_DIR: additionally requires DEST to be a path with at least
# one slash component whose last component is `opencode` (or `opencode-*`,
# which is what the sandboxed test dir used in verification is called).
# Anything else is refused. Only the destructive targets use this.
# -----------------------------------------------------------------------------
define REQUIRE_DEST
	@dest='$(DEST)'; \
	if [[ -z "$$dest" || "$$dest" == / ]]; then \
		printf 'error: DEST is empty or "/" — refusing to continue.\n' >&2; \
		printf 'error: usage: make DEST=<dir ending in /opencode> <target>\n' >&2; \
		exit 1; \
	fi
endef

define REQUIRE_OPENCODE_DIR
	@dest='$(DEST)'; path=$${dest%/}; base=$${path:t}; \
	if [[ "$$path" != */* || ( "$$base" != opencode && "$$base" != opencode-* ) ]]; then \
		printf 'error: refusing to run: DEST=%s does not look like an opencode config dir.\n' "'$$dest'" >&2; \
		printf 'error: DEST must end in /opencode (e.g. $$HOME/.config/opencode)\n' >&2; \
		exit 1; \
	fi
endef

# -----------------------------------------------------------------------------
# Copy logic — shared by `deploy` and `reinstall` so they can never drift.
# `deploy` and `reinstall` therefore produce byte-identical results.
# -----------------------------------------------------------------------------
# `skills/.` (not `skills/*`) is copied so dotfiles inside skills/ survive too.
define COPY_CMDS
	@mkdir -p "$(AGENTS_DEST)" "$(SKILLS_DEST)"
	@cp -f "$(SRC)/agent"/*.md "$(AGENTS_DEST)/"
	@cp -Rf "$(SRC)/skills/." "$(SKILLS_DEST)/"
	@cp -f "$(SRC)/opencode.json" "$(CONFIG_DEST)"
	@printf 'installed -> %s\n' '$(DEST)'
endef

# -----------------------------------------------------------------------------
# Removal logic — shared by `reinstall` and `clean`.
#
# NOTE: we remove the whole `agent/` and `skills/` directories rather than doing
# `rm -rf "$(AGENTS_DEST)"/*`. A `dir/*` glob does not match dotfiles, so it
# would silently leave stale dotfiles behind and the "content is replaced"
# promise would be a lie. Dropping the directory and letting COPY_CMDS
# `mkdir -p` it again is both simpler and actually complete. $(DEST) itself,
# plus anything else living in it (node_modules/, .gitignore, ...) is untouched.
#
# BOTH spellings are removed for each kind. opencode scans `{agent,agents}` and
# `{skill,skills}`, so an install from an earlier revision of this Makefile may
# have left a `skill/` or `agents/` tree behind. Deleting only the spelling we
# install today would let that stale tree survive and collide with the fresh one
# on duplicate skill names.
# -----------------------------------------------------------------------------
define CLEAN_CMDS
	@rm -rf "$(AGENTS_DEST)" "$(DEST)/agents"
	@rm -rf "$(SKILLS_DEST)" "$(DEST)/skill"
	@rm -f "$(CONFIG_DEST)"
	@printf 'removed agent/, agents/, skills/, skill/ and opencode.json from %s\n' '$(DEST)'
endef

# -----------------------------------------------------------------------------
# Permission-mirror check
# -----------------------------------------------------------------------------
# The bash deny-list now exists in four places: `opencode.json` -> permission.bash
# and the three agent files that mirror it. Hand edits and parallel dispatches
# make those drift, and the drift is silent: the harness keeps installing, only
# the runtime permissions change. `check` is a gate, not a report — it exits
# non-zero on any violation, and it runs before `deploy` and `reinstall` copy
# anything, so a drifting tree can never reach $(DEST).
#
# Two properties make it impossible to pass vacuously:
#   1. Every extraction prints the number of rules and deny patterns it read, for
#      every file, and the caller requires the deny count to be >= MIN_DENY. A
#      reformat that yields zero patterns (e.g. opencode.json re-serialised to a
#      single line) fails loudly instead of reporting `[] == []` as a pass.
#   2. The global and agent lists are compared with `diff`, i.e. ordered, not as
#      sets — rule order is load-bearing in V1 (last matching rule wins), so a
#      reorder is a behaviour change, not a cosmetic one.
#
# Assertions:
#   A1  no agent frontmatter declares a bare-scalar `bash:` whose value is
#       anything other than `deny`. A bare scalar becomes a single wildcard rule
#       appended AFTER the global rules, so `bash: allow` overrides every global
#       bash deny — that was the original defect. A bare `bash: deny` cannot
#       widen anything and stays legal: daedalus.md and dispatcher.md declare it,
#       and this check must not force a rewrite of files it is not here to change.
#   A2  "*" is the first key of every object-form `bash` block, and of the global
#       permission.bash. Any earlier rule is shadowed by the wildcard under
#       last-match-wins, which silently turns a deny into an allow.
#   A3  ordered equality of the deny patterns between opencode.json and each of
#       the three mirroring agents.
#   A4  "*": deny is the first key of each agent's permission block. Load-bearing
#       and previously undocumented: agent rules land AFTER the global
#       external_directory rules (indices ~94 vs ~87-92), so this catch-all is
#       what currently resolves external_directory — and with it the credential
#       paths — to deny.
#   A5  no agent frontmatter declares a bare `write:` key. `write` is not a V1
#       permission key — file modification is gated by `edit`, which covers
#       write/edit/apply_patch — so the rule can never be a candidate and only
#       reads as if it were load-bearing. Deleting `edit:` while a dead `write:`
#       remained would look safe and fail open.
#   A6  every agent's `skill` permission block lists exactly the skill names in
#       that agent's own "## Load these skills" table, and `"*": deny` is its
#       first key. The table is the human-facing scope; the block is what the
#       runtime enforces. When they drift the failure is silent in both
#       directions: an allow with no table entry is an undocumented capability,
#       a table entry with no allow is a skill the agent is told to load and
#       cannot. Unlike A3 this is compared as a SET — rule order is not
#       load-bearing here, because `"*": deny` is first and the named allows
#       match disjoint patterns, so none can shadow another. Both sides must be
#       non-empty (MIN_SKILLS) or A6 refuses to compare two empty lists.
#   A7  every agent's `task` permission is explicitly scoped, and every agent it
#       names is one that exists. Three parts:
#         1. no bare-scalar `task:` whose action is anything other than `deny`.
#            Same reasoning as A1: a bare scalar is appended AFTER the global
#            rules and resolves to a wildcard that reaches every agent,
#            Dispatcher included -- and a subagent that can create a subagent
#            that can create a subagent is the loop this exists to prevent.
#            `task: deny` (jeff.md) cannot widen anything and stays legal, the
#            same way A1 keeps `bash: deny` legal on dispatcher.md/daedalus.md.
#         2. "*" is the first key of every object-form `task` block, read as
#            tolerantly as A2 reads it: `"*"` followed by any action, with or
#            without the trailing comma the flow-mapping spelling leaves behind
#            (dispatcher.md, sherlock.md and daedalus.md all use that spelling).
#         3. every named ALLOW is the frontmatter `name:` of a defined agent,
#            byte for byte and case for case. This is the part that catches a
#            silent, inert grant: `"sherlock": allow` resolves to a rule that can
#            never match anything, so the agent quietly becomes undispatchable
#            and nothing anywhere reports an error. `Dispatcher` vs `dispatcher`
#            was already a live ambiguity in this repo, so it is asserted here
#            rather than left to review.
#       Both sides are counted and floored before they are compared: one `name:`
#       per agent file, and at least MIN_TASK_ALLOWS named allows per
#       object-form block. Refusing to compare two empty lists is the whole
#       point -- stripping a `task:` key outright has to FAIL, not extract zero
#       from each side and call it a match.
#   A8  every agent declares an OBJECT-FORM `external_directory` block whose
#       rules are exactly `"*": ask` followed by the five credential paths as
#       `deny` -- identical, and in identical order, in all six agents.
#       Load-bearing, and this is the assertion A4's comment was written
#       against: without the block, each agent's `"*": deny` (rule ~93) wins
#       every external-directory question, so a sibling repo, /etc and the
#       credential paths are all hard-denied with no operator prompt and no
#       runtime override, and the five global credential denies at rules 87-91
#       are shadowed in every case and contribute nothing. Order is the whole
#       policy here, so the comparison is an ORDERED diff against one
#       reference list, not a set diff -- `"*"` last would make the credential
#       denies resolve to `ask`, a clickable prompt on `~/.aws/**`, which is
#       strictly less safe than what it replaced.
#   A9  every agent declares an OBJECT-FORM `read` block whose first rule is
#       `"*": allow`, which contains `*.env: deny` and `*.env.*: deny`, and in
#       which every `*.env.example` / `*.env.sample` / `*.env.template` allow
#       appears AFTER `*.env.*`. Both halves are load-bearing: a bare
#       `read: allow` is appended after the global rules and wins opencode's
#       built-in `*.env` rule, which is `ask` -- not `deny`, as the docs
#       claim -- so `.env` files are readable and a runtime probe returned a
#       secret canary from one. And `*.env.*` matches `.env.example`, so a
#       template allow placed before it is inert and blocks a committed
#       template. The SET of template allowances is an operator judgement call
#       and is deliberately not pinned; only their presence-after-`*.env.*` is
#       asserted.
#
# Tools: awk, diff, wc, sed, mktemp. No python3 and no jq: the repo had no such
# dependency and `check` does not add one. Parsing is line- and indentation-
# driven against the shape this repo actually writes; it is not a general
# YAML/JSON parser and does not pretend to be. An unrecognised shape yields zero
# extracted patterns, which MIN_DENY, MIN_SKILLS, MIN_TASK_ALLOWS,
# MIN_READ_RULES or the A8 reference count then rejects as a failure rather
# than a pass.
# -----------------------------------------------------------------------------

# Agents that must carry the full deny-list.
AGENTS_MIRROR := jeff jozef sherlock

# Every agent present, for the shape-only assertions (A1, A4, A5, A7).
AGENTS_ALL := $(sort $(notdir $(basename $(wildcard $(SRC)/agent/*.md))))

# Deny patterns every mirrored file must carry. A lower bound rather than an
# exact count, so adding a deny rule to all four files stays legal — but the
# count is always printed and must never fall below this.
MIN_DENY := 19

# Skill names every agent's `skill` block AND its "## Load these skills" table
# must both carry, for the same vacuity reason as MIN_DENY. The smallest table
# today is eight — Daedalus, Dispatcher and Michal each name eight — so 8 is the
# floor: a reformatted or truncated table cannot quietly fall to zero, or shed a
# row, and be compared against a permission block as a pass.
MIN_SKILLS := 8

# Named `task` allows every object-form `task:` block must carry, for the same
# vacuity reason as MIN_DENY and MIN_SKILLS. The smallest such block today is
# one entry wide -- sherlock.md and daedalus.md each name exactly one target,
# Jeff -- so 1 is the floor; michal.md and jozef.md name two and dispatcher.md
# names five. Without a floor an emptied or stripped block extracts zero names,
# compares them against the agent-name list, and reports a vacuous pass on the
# one comparison that matters most.
MIN_TASK_ALLOWS := 1

# A8's reference list: the credential paths every agent must re-declare as
# `deny` in its own `external_directory` block, IN THIS ORDER, after its `"*"`
# wildcard. This is the same five and the same order as the global block in
# opencode.json, which is the reference list the task was written against; it is
# spelled out here rather than extracted from opencode.json on purpose. A3
# already asserts the bash deny-lists are identical in both files, but a gate
# that reads its expectation out of the file it is checking can be satisfied by
# changing both at once, which is the wrong failure mode for a security
# boundary. opencode.json is not edited by this Makefile at all.
CREDENTIAL_DENIES := ~/.ssh/** ~/.aws/** ~/.config/gcloud/** ~/.kube/** ~/.gnupg/**
CREDENTIAL_DENIES_N := $(words $(CREDENTIAL_DENIES))

# Rules every agent's object-form `read:` block must carry, for the same
# vacuity reason as MIN_DENY and MIN_SKILLS: the wildcard plus the two `.env`
# denies. A bare `read: allow` scalar, or a `read:` key stripped outright,
# extracts zero and must FAIL rather than be compared against an empty list.
# The floor is deliberately 3 and not 6: the `*.env.example` / `.sample` /
# `.template` allowances are an operator judgement call (they keep committed
# templates readable, which the built-in rule set does not), so A9 asserts
# their ORDER rather than pinning which ones exist.
MIN_READ_RULES := 3

# AWK_JSON_BASH: awk source printing the deny patterns of `permission.bash` from
# an opencode.json, one per line, in file order; reports the counts to stderr.
define AWK_JSON_BASH
	/"bash"[[:space:]]*:[[:space:]]*{/ { inb = 1; next } \
	inb && /^[[:space:]]*}/ { inb = 0; next } \
	!inb { next } \
	/^[[:space:]]*"/ { \
	  s = $$0; sub(/^[[:space:]]*"/, "", s); \
	  q = index(s, "\""); if (q == 0) next; \
	  pat = substr(s, 1, q - 1); \
	  a = substr(s, q + 1); \
	  sub(/^[[:space:]]*:[[:space:]]*"?/, "", a); sub(/"?[[:space:]]*,?[[:space:]]*$$/, "", a); \
	  n++; if (a == "deny") { print pat; c++ } \
	} \
	END { printf "check:   read %d rule(s), %d deny pattern(s) from %s\n", n + 0, c + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_YAML_BASH: awk source printing the deny patterns of an agent file's
# object-form `bash:` block, one per line, in file order; reports the counts to
# stderr. Scoped to the frontmatter (delimited by `---`) and to the block mapping
# at indent 4, so it cannot wander into the prose body or a nested `task:` map.
define AWK_YAML_BASH
	NR == 1 && $$0 == "---" { fm = 1; next } \
	NR == 1 { fm = 0 } \
	fm && $$0 == "---" { fm = 0; next } \
	!fm { next } \
	/^  bash:[[:space:]]*$$/ { inb = 1; next } \
	inb && /^  [^[:space:]#]/ { inb = 0 } \
	!inb { next } \
	/^[[:space:]]*#/ { next } \
	{ \
	  s = $$0; sub(/^[[:space:]]*"/, "", s); \
	  q = index(s, "\""); if (q == 0) next; \
	  pat = substr(s, 1, q - 1); \
	  a = substr(s, q + 1); \
	  sub(/^[[:space:]]*:[[:space:]]*/, "", a); sub(/[[:space:]]*$$/, "", a); \
	  n++; if (a == "deny") { print pat; c++ } \
	} \
	END { printf "check:   read %d rule(s), %d deny pattern(s) from %s bash block\n", n + 0, c + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_YAML_SKILL: awk source printing the named skill keys of an agent file's
# object-form `skill:` block, one per line, in file order; reports the count to
# stderr. The `"*"` wildcard key is skipped — A6 checks it separately and by
# position, not by membership. Scoped to the frontmatter and to the block
# mapping at indent 4, the same scoping as AWK_YAML_BASH, so a `skill:` mention
# in the prose body cannot be read as a permission.
define AWK_YAML_SKILL
	NR == 1 && $$0 == "---" { fm = 1; next } \
	NR == 1 { fm = 0 } \
	fm && $$0 == "---" { fm = 0; next } \
	!fm { next } \
	/^  skill:[[:space:]]*$$/ { inb = 1; next } \
	inb && /^  [^[:space:]#]/ { inb = 0 } \
	!inb { next } \
	/^[[:space:]]*#/ { next } \
	{ \
	  s = $$0; sub(/^[[:space:]]*"/, "", s); \
	  q = index(s, "\""); if (q == 0) next; \
	  name = substr(s, 1, q - 1); \
	  n++; if (name != "*") print name; \
	} \
	END { printf "check:   read %d skill rule(s) from %s skill block\n", n + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_YAML_TASK: awk source printing the named ALLOWED agents of an agent file's
# object-form `task:` block, one per line, in file order; reports the counts to
# stderr. Same frontmatter and indent-4 scoping as AWK_YAML_SKILL, and it reads
# both spellings this repo writes for an object-form block: the block mapping
# (`task:` then indented entries) and the flow mapping (`task: {` then the same
# indented entries, closed by `  }`) that dispatcher.md, sherlock.md and
# daedalus.md use. The action token is compared literally after stripping the
# JSON-style trailing comma and optional quotes, so `"allow",` and `allow` are
# the same rule -- the trailing comma is a real property of that spelling, not a
# formatting mistake to be worked around. Only entries whose action is `allow`
# are printed: A7's third part is about inert ALLOWS, and a deny naming a
# non-existent agent is inert but harmless. The `"*"` wildcard key is skipped --
# A7 checks it separately and by position.
define AWK_YAML_TASK
	NR == 1 && $$0 == "---" { fm = 1; next } \
	NR == 1 { fm = 0 } \
	fm && $$0 == "---" { fm = 0; next } \
	!fm { next } \
	/^  task:[[:space:]]*$$/ { inb = 1; next } \
	/^  task:[[:space:]]*\{/ { inb = 1; next } \
	inb && /^  [^[:space:]#]/ { inb = 0 } \
	!inb { next } \
	/^[[:space:]]*#/ { next } \
	{ \
	  s = $$0; sub(/^[[:space:]]*"/, "", s); \
	  q = index(s, "\""); if (q == 0) next; \
	  name = substr(s, 1, q - 1); \
	  a = substr(s, q + 1); \
	  sub(/^[[:space:]]*:[[:space:]]*/, "", a); sub(/[[:space:]]*$$/, "", a); \
	  sub(/,[[:space:]]*$$/, "", a); sub(/^"/, "", a); sub(/"$$/, "", a); \
	  n++; if (name != "*") { c++; if (a == "allow") print name; } \
	} \
	END { printf "check:   read %d task rule(s), %d named allow(s) from %s task block\n", n + 0, c + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_YAML_EXTDIR: awk source printing every entry of an agent file's
# object-form `external_directory:` block as `pattern<TAB>action`, one per line,
# in file order; reports the count to stderr. Same frontmatter and indent-4
# scoping as AWK_YAML_TASK, and it reads both spellings: the block mapping and
# the flow mapping (`external_directory: {` ... `  }`) that all six agents use.
#
# The action is printed as well as the pattern, and normalised exactly the way
# AWK_YAML_TASK normalises it (JSON-style trailing comma and optional quotes
# stripped), because A8 has to be able to tell `"*": ask` from `"*": deny` --
# the two are opposite policy, and comparing patterns alone would pass a block
# whose wildcard denies everything, which is the defect this assertion exists
# to end. Order is preserved verbatim rather than sorted, because under
# last-match-wins the order IS the policy.
define AWK_YAML_EXTDIR
	NR == 1 && $$0 == "---" { fm = 1; next } \
	NR == 1 { fm = 0 } \
	fm && $$0 == "---" { fm = 0; next } \
	!fm { next } \
	/^  external_directory:[[:space:]]*$$/ { inb = 1; next } \
	/^  external_directory:[[:space:]]*\{/ { inb = 1; next } \
	inb && /^  [^[:space:]#]/ { inb = 0 } \
	!inb { next } \
	/^[[:space:]]*#/ { next } \
	{ \
	  s = $$0; sub(/^[[:space:]]*"/, "", s); \
	  q = index(s, "\""); if (q == 0) next; \
	  pat = substr(s, 1, q - 1); \
	  a = substr(s, q + 1); \
	  sub(/^[[:space:]]*:[[:space:]]*/, "", a); sub(/[[:space:]]*$$/, "", a); \
	  sub(/,[[:space:]]*$$/, "", a); sub(/^"/, "", a); sub(/"$$/, "", a); \
	  n++; printf "%s\t%s\n", pat, a; \
	} \
	END { printf "check:   read %d external_directory rule(s) from %s external_directory block\n", n + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_YAML_READ: awk source printing every entry of an agent file's object-form
# `read:` block as `pattern<TAB>action`, in file order; reports the count to
# stderr. Identical scoping and action normalisation to AWK_YAML_EXTDIR, which
# is what lets one AWK_READ_ORDER check consume either list.
#
# A bare `read: allow` scalar does not match either header pattern and therefore
# extracts nothing -- deliberately, so that MIN_READ_RULES rejects it as a shape
# error rather than the block being silently read as empty-but-fine.
define AWK_YAML_READ
	NR == 1 && $$0 == "---" { fm = 1; next } \
	NR == 1 { fm = 0 } \
	fm && $$0 == "---" { fm = 0; next } \
	!fm { next } \
	/^  read:[[:space:]]*$$/ { inb = 1; next } \
	/^  read:[[:space:]]*\{/ { inb = 1; next } \
	inb && /^  [^[:space:]#]/ { inb = 0 } \
	!inb { next } \
	/^[[:space:]]*#/ { next } \
	{ \
	  s = $$0; sub(/^[[:space:]]*"/, "", s); \
	  q = index(s, "\""); if (q == 0) next; \
	  pat = substr(s, 1, q - 1); \
	  a = substr(s, q + 1); \
	  sub(/^[[:space:]]*:[[:space:]]*/, "", a); sub(/[[:space:]]*$$/, "", a); \
	  sub(/,[[:space:]]*$$/, "", a); sub(/^"/, "", a); sub(/"$$/, "", a); \
	  n++; printf "%s\t%s\n", pat, a; \
	} \
	END { printf "check:   read %d read rule(s) from %s read block\n", n + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_READ_ORDER: awk source consuming an AWK_YAML_READ-extracted
# `pattern<TAB>action` list and printing one line per ORDERING problem, the way
# AWK_SET_DIFF prints one line per naming difference. Prints nothing when the
# block is sound, so the caller tests for emptiness.
#
# Three separate defects are reported rather than one "block is wrong", because
# they have different fixes and only one of them is invisible in review:
#   1. `*.env` or `*.env.*` is absent, or present with an action other than
#      deny. Absence is the shape error MIN_READ_RULES already catches; the
#      action being something else is the silent half and is only visible here.
#   2. A template allow sits BEFORE `*.env.*`: deny. `*.env.*` matches
#      `.env.example`, so under last-match-wins the deny wins and the template
#      allowance is an inert rule that reads as if it granted something.
# The template set is a regex, not a literal list, so adding `.env.dist` or
# dropping `.env.sample` does not need a change here; only the ORDER is fixed.
# Positions are 1-based over the extracted rules, which is the order opencode
# resolves, so the numbers in a failure message can be read straight off the
# agent's own `read:` block.
define AWK_READ_ORDER
	{ \
	  i++; \
	  line = $$0; t = index(line, "\t"); \
	  if (t > 0) { pat = substr(line, 1, t - 1); act = substr(line, t + 1) } \
	  else { pat = line; act = "" } \
	  if (pat == "*.env") { s1 = 1; if (act == "deny") d1 = i } \
	  else if (pat == "*.env.*") { s2 = 1; if (act == "deny") d2 = i } \
	  else if (pat ~ /^\*\.env\.(example|sample|template)$$/) { \
	    nt++; tpat[nt] = pat; tact[nt] = act; tpos[nt] = i } \
	} \
	END { \
	  bad = 0; \
	  if (!s1) { printf "      no rule for \"*.env\" at all\n"; bad++ } \
	  else if (!d1) { printf "      \"*.env\" is declared but its action is not deny\n"; bad++ } \
	  if (!s2) { printf "      no rule for \"*.env.*\" at all\n"; bad++ } \
	  else if (!d2) { printf "      \"*.env.*\" is declared but its action is not deny\n"; bad++ } \
	  if (d2 + 0 > 0) { \
	    for (k = 1; k <= nt + 0; k++) if (tpos[k] + 0 < d2 + 0) { \
	      printf "      %s: %s is at #%d, BEFORE \"*.env.*\": deny at #%d -- last-match-wins makes it inert\n", tpat[k], tact[k], tpos[k], d2; \
	      bad++ } \
	  } \
	  printf "check:   %d read-ordering problem(s) in %d rule(s); \"*.env\" deny at #%d, \"*.env.*\" deny at #%d, %d template allow(s)\n", bad + 0, i + 0, d1 + 0, d2 + 0, nt + 0 > "/dev/stderr"; \
	}
endef

# AWK_MD_AGENTNAME: awk source printing each agent file's frontmatter `name:`
# value, one per line; reports the count to stderr. This is the universe A7
# compares named `task` allows against, and it is the frontmatter key rather
# than the filename because that is what V1 addresses agents by -- `Dispatcher`
# resolves and `dispatcher` does not.
#
# This is the one extractor that is handed EVERY agent file in a single awk run,
# so it re-arms per file instead of using the `NR == 1` idiom the single-file
# extractors above use. Two states must reset: `fm` (are we between the `---`
# fences) and `got` (have we read this file's name). awk's END runs once for the
# whole run, so a flag left set by the first file silently starves the rest --
# which reads as a one-agent universe and then fails every file against it.
define AWK_MD_AGENTNAME
	FNR == 1 { fm = ($$0 == "---"); got = 0; nf++; next } \
	!fm { next } \
	$$0 == "---" { fm = 0; next } \
	/^name:/ && !got { \
	  got = 1; s = $$0; sub(/^name:[[:space:]]*/, "", s); sub(/[[:space:]]*$$/, "", s); \
	  sub(/^"/, "", s); sub(/"$$/, "", s); \
	  if (s != "") { print s; n++ } \
	} \
	END { printf "check:   read %d agent name(s) from %d agent file(s)\n", n + 0, nf + 0 > "/dev/stderr"; }
endef

# AWK_MD_SKILL: awk source printing the backticked skill names from an agent
# file's "## Load these skills" table, one per line, in file order; reports the
# count to stderr. Only the FIRST column is read, so prose in the "When to load
# it" column — which may legitimately contain backticks, e.g. Jeff's
# "`definition-of-done`, then `handoff-report`" — cannot inject a name. The
# table ends at the next `## ` heading or EOF.
define AWK_MD_SKILL
	/^## Load these skills[[:space:]]*$$/ { intbl = 1; next } \
	intbl && /^## / { intbl = 0 } \
	!intbl { next } \
	/^[[:space:]]*\|/ { \
	  line = $$0; \
	  sub(/^[^|]*\|/, "", line); \
	  p = index(line, "|"); \
	  if (p > 0) line = substr(line, 1, p - 1); \
	  while (match(line, /`[^`]+`/)) { \
	    tok = substr(line, RSTART + 1, RLENGTH - 2); \
	    if (tok != "") { print tok; n++ } \
	    line = substr(line, RSTART + RLENGTH); \
	  } \
	} \
	END { printf "check:   read %d skill name(s) from the %s table\n", n + 0, FILENAME > "/dev/stderr"; }
endef

# AWK_SET_DIFF: awk source printing the symmetric difference of two name lists
# as "only in permission: X" / "only in table: X" lines, comparing as SETS.
# Unlike A3 (which must compare in order, because rule order is load-bearing
# under last-match-wins), skill name order carries no meaning — the block's
# `"*": deny` is first and the named allows match disjoint patterns. Set
# comparison also keeps the report readable: one name per line, both directions
# named explicitly, so a failure names the offending skill.
define AWK_SET_DIFF
	NR == FNR { if (length($$0) > 0) a[$$0] = 1; next } \
	{ if (length($$0) > 0) { b[$$0] = 1 } } \
	END { \
	  for (k in a) if (!(k in b)) printf "      only in the permission block: %s\n", k; \
	  for (k in b) if (!(k in a)) printf "      only in the table: %s\n", k; \
	}
endef

# AWK_NOT_IN: awk source printing every non-empty line of the FIRST file that
# does not appear, byte for byte, in the second; reports the count to stderr.
# Arguments are (list under test, reference universe) -- the same order
# AWK_SET_DIFF's caller uses. The first file is buffered rather than compared on
# the fly because the universe is the second file and is therefore not known
# until it has been read; buffering also keeps the output in file order, so a
# failure lists the offending names the way the block declares them instead of in
# awk's unspecified hash order.
#
# One direction only, which is the difference from AWK_SET_DIFF: A7 asks whether
# each named `task` allow IS a defined agent, not whether every defined agent is
# allowed. An agent that delegates to nobody is correct (jeff.md is `task: deny`)
# and must never be reported. Matching is whole-line and case-sensitive on
# purpose -- `sherlock` is not `Sherlock`, and that is the whole defect.
define AWK_NOT_IN
	NR == FNR { if (length($$0) > 0) first[++nf1] = $$0; next } \
	{ if (length($$0) > 0) b[$$0] = 1 } \
	END { \
	  for (i = 1; i <= nf1 + 0; i++) if (!(first[i] in b)) { print first[i]; n++ } \
	  printf "check:   %d of %d named task allow(s) name no defined agent\n", n + 0, nf1 + 0 > "/dev/stderr" \
	}
endef

define CHECK_CMDS
	@fail=0; \
	tmp=$$(mktemp -d "$${TMPDIR:-/tmp}/opencode-check.XXXXXX") || { printf 'error: cannot create a temp directory.\n' >&2; exit 1; }; \
	trap 'rm -rf "$$tmp"' EXIT INT TERM; \
	global=$$(awk '$(AWK_JSON_BASH)' "$(SRC)/opencode.json"); \
	printf '%s\n' "$$global" > "$$tmp/global.txt"; \
	gcount=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/global.txt"); \
	gfirst=$$(awk '/"bash"[[:space:]]*:[[:space:]]*{/ { inb = 1; next } inb && /^[[:space:]]*}/ { inb = 0 } inb && /^[[:space:]]*"/ { s = $$0; sub(/^[[:space:]]*"/, "", s); sub(/".*/, "", s); print s; exit }' "$(SRC)/opencode.json"); \
	if [ "$$gfirst" != '*' ]; then \
		printf 'FAIL A2: %s/opencode.json permission.bash first key is `%s`.\n' "$(SRC)" "$${gfirst:-<none>}" >&2; \
		printf 'FAIL A2: expected: "*" — under last-match-wins a later wildcard shadows any earlier rule.\n' >&2; \
		fail=1; \
	fi; \
	if [ "$$gcount" -eq 0 ]; then \
		printf 'FAIL A3: extracted 0 deny patterns from %s/opencode.json.\n' "$(SRC)" >&2; \
		printf 'FAIL A3: expected at least %d. Refusing to compare an empty global list against anything.\n' "$(MIN_DENY)" >&2; \
		fail=1; \
	elif [ "$$gcount" -lt "$(MIN_DENY)" ]; then \
		printf 'FAIL A3: %s/opencode.json has %d deny pattern(s), expected at least %d.\n' "$(SRC)" "$$gcount" "$(MIN_DENY)" >&2; \
		fail=1; \
	fi; \
	filesn=$$(printf '%s\n' $(AGENTS_ALL) | awk 'length($$0) > 0 { c++ } END { print c + 0 }'); \
	if [ "$$filesn" -eq 0 ]; then \
		printf 'FAIL A7: found no agent file under %s/agent/.\n' "$(SRC)" >&2; \
		printf 'FAIL A7: expected one agent per file, each declaring a frontmatter `name:`. Refusing to compare a task allowlist against an empty set of agent names.\n' >&2; \
		fail=1; \
		namesn=0; \
	else \
		names=$$(awk '$(AWK_MD_AGENTNAME)' $(addprefix $(SRC)/agent/,$(addsuffix .md,$(AGENTS_ALL)))); \
		printf '%s\n' "$$names" > "$$tmp/agentnames.txt"; \
		namesn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/agentnames.txt"); \
		if [ "$$namesn" -eq 0 ]; then \
			printf 'FAIL A7: extracted 0 agent name(s) from the frontmatter of %s/agent/*.md.\n' "$(SRC)" >&2; \
			printf 'FAIL A7: expected one `name:` per agent file -- agent IDs are the frontmatter name, never the filename. Refusing to compare an empty list against anything.\n' >&2; \
			fail=1; \
		elif [ "$$namesn" -ne "$$filesn" ]; then \
			printf 'FAIL A7: extracted %d agent name(s) from %d agent file(s).\n' "$$namesn" "$$filesn" >&2; \
			printf 'FAIL A7: expected exactly one `name:` per file. A missing or duplicated name makes every task allowlist ambiguous, and the duplicate would silently narrow the universe.\n' >&2; \
			fail=1; \
		fi; \
	fi; \
	awk -v 'pats=$(CREDENTIAL_DENIES)' 'BEGIN { n = split(pats, a, " "); print "*\task"; for (i = 1; i <= n; i++) print a[i] "\tdeny" }' > "$$tmp/extdir.ref.txt"; \
	xrefn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/extdir.ref.txt"); \
	if [ "$$xrefn" -eq 0 ]; then \
		printf 'FAIL A8: built an empty external_directory reference list.\n' >&2; \
		printf 'FAIL A8: expected 1 wildcard entry plus %d credential deny pattern(s). Refusing to compare any agent block against an empty reference.\n' "$(CREDENTIAL_DENIES_N)" >&2; \
		fail=1; \
	fi; \
	for a in $(AGENTS_ALL); do \
		f="$(SRC)/agent/$$a.md"; \
		if [ ! -f "$$f" ]; then \
			printf 'FAIL A0: missing agent file %s.\n' "$$f" >&2; fail=1; continue; \
		fi; \
		scalar=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  bash:/ { s = $$0; sub(/^  bash:[[:space:]]*/, "", s); if (s != "") print s; exit }' "$$f"); \
		if [ -n "$$scalar" ] && [ "$$scalar" != '{' ] && [ "$$scalar" != 'deny' ]; then \
			printf 'FAIL A1: %s declares bare-scalar `bash: %s`.\n' "$$f" "$$scalar" >&2; \
			printf 'FAIL A1: expected: object-form bash block with "*" first. A bare scalar is appended after the global rules and overrides every global bash deny.\n' >&2; \
			fail=1; \
		fi; \
		wk=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  write:/ { s = $$0; sub(/^[[:space:]]*/, "", s); print s; exit }' "$$f"); \
		if [ -n "$$wk" ]; then \
			printf 'FAIL A5: %s declares `%s`.\n' "$$f" "$$wk" >&2; \
			printf 'FAIL A5: expected: no `write:` key. `write` is not a V1 permission key; `edit` is what gates file modification.\n' >&2; \
			fail=1; \
		fi; \
		pfirst=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^permission:[[:space:]]*$$/ { inp = 1; next } inp && /^[^[:space:]#]/ { exit } inp && /^  [^[:space:]#]/ { s = $$0; sub(/^[[:space:]]*/, "", s); print s; exit }' "$$f"); \
		if [ "$$pfirst" != '"*": deny' ]; then \
			printf 'FAIL A4: %s permission block first key is `%s`.\n' "$$f" "$${pfirst:-<none>}" >&2; \
			printf 'FAIL A4: expected: "*": deny. Agent rules land after the global external_directory rules, so this catch-all is what resolves them — and the credential paths — to deny.\n' >&2; \
			fail=1; \
		fi; \
		sfirst=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  skill:[[:space:]]*$$/ { inb = 1; next } inb && /^  [^[:space:]#]/ { inb = 0 } inb && /^    [^[:space:]#]/ { s = $$0; sub(/^[[:space:]]*/, "", s); print s; exit }' "$$f"); \
		if [ "$$sfirst" != '"*": deny' ]; then \
			printf 'FAIL A6: %s skill block first key is `%s`.\n' "$$f" "$${sfirst:-<none>}" >&2; \
			printf 'FAIL A6: expected: "*": deny. The global opencode.json skill rule is appended BEFORE the agent rules, so an agent without its own catch-all inherits the global "*" allow for every skill.\n' >&2; \
			fail=1; \
		fi; \
		sperm=$$(awk '$(AWK_YAML_SKILL)' "$$f"); \
		printf '%s\n' "$$sperm" > "$$tmp/$$a.skillperm.txt"; \
		spermn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/$$a.skillperm.txt"); \
		if [ "$$spermn" -eq 0 ]; then \
			printf 'FAIL A6: extracted 0 named skill(s) from the permission block of %s.\n' "$$f" >&2; \
			printf 'FAIL A6: expected an object-form `skill:` block with `"*": deny` plus at least %d named allow(s). Refusing to compare an empty permission list against anything.\n' "$(MIN_SKILLS)" >&2; \
			fail=1; \
		elif [ "$$spermn" -lt "$(MIN_SKILLS)" ]; then \
			printf 'FAIL A6: %s permission block names %d skill(s), expected at least %d.\n' "$$f" "$$spermn" "$(MIN_SKILLS)" >&2; \
			fail=1; \
		fi; \
		stab=$$(awk '$(AWK_MD_SKILL)' "$$f"); \
		printf '%s\n' "$$stab" > "$$tmp/$$a.skilltable.txt"; \
		stabn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/$$a.skilltable.txt"); \
		if [ "$$stabn" -eq 0 ]; then \
			printf 'FAIL A6: extracted 0 skill name(s) from the "## Load these skills" table of %s.\n' "$$f" >&2; \
			printf 'FAIL A6: expected a markdown table whose first column backticks at least %d skill name(s). Refusing to compare an empty table against anything.\n' "$(MIN_SKILLS)" >&2; \
			fail=1; \
		elif [ "$$stabn" -lt "$(MIN_SKILLS)" ]; then \
			printf 'FAIL A6: %s table names %d skill(s), expected at least %d.\n' "$$f" "$$stabn" "$(MIN_SKILLS)" >&2; \
			fail=1; \
		fi; \
		if [ "$$spermn" -gt 0 ] && [ "$$stabn" -gt 0 ]; then \
			sdiff=$$(awk '$(AWK_SET_DIFF)' "$$tmp/$$a.skillperm.txt" "$$tmp/$$a.skilltable.txt"); \
			if [ -n "$$sdiff" ]; then \
				printf 'FAIL A6: skill names in the `skill:` permission block of %s differ from its "## Load these skills" table.\n' "$$f" >&2; \
				printf '      %d name(s) in the permission block, %d in the table. Difference:\n' "$$spermn" "$$stabn" >&2; \
				printf '%s\n' "$$sdiff" >&2; \
				printf 'FAIL A6: the table is the documented scope and the block is what the runtime enforces; keep them identical.\n' >&2; \
				fail=1; \
			fi; \
		fi; \
		tscalar=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  task:/ { s = $$0; sub(/^  task:[[:space:]]*/, "", s); sub(/[[:space:]]*$$/, "", s); sub(/^"/, "", s); sub(/"$$/, "", s); if (s != "") print s; exit }' "$$f"); \
		if [ -n "$$tscalar" ] && [ "$$tscalar" != '{' ] && [ "$$tscalar" != 'deny' ]; then \
			printf 'FAIL A7: %s declares bare-scalar `task: %s`.\n' "$$f" "$$tscalar" >&2; \
			printf 'FAIL A7: expected: object-form task block with "*" first, or `task: deny`. A bare scalar is appended after the global rules and reaches every agent, Dispatcher included.\n' >&2; \
			fail=1; \
		fi; \
		if [ -z "$$tscalar" ] || [ "$$tscalar" = '{' ]; then \
			tfirst=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  task:[[:space:]]*$$/ { inb = 1; next } /^  task:[[:space:]]*\{/ { inb = 1; next } inb && /^    [^[:space:]#]/ { s = $$0; sub(/^[[:space:]]*/, "", s); print s; exit }' "$$f"); \
			case "$$tfirst" in \
				'"*": '*|*'"*":'*) ;; \
				*) printf 'FAIL A7: %s task block first key is `%s`.\n' "$$f" "$${tfirst:-<none>}" >&2; \
				   printf 'FAIL A7: expected: "*" first (e.g. "*": deny). A wildcard placed after a named rule shadows it under last-match-wins, silently turning that deny into an allow.\n' >&2; \
				   fail=1 ;; \
			esac; \
		fi; \
		tperm=$$(awk '$(AWK_YAML_TASK)' "$$f"); \
		printf '%s\n' "$$tperm" > "$$tmp/$$a.taskperm.txt"; \
		tpermn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/$$a.taskperm.txt"); \
		if [ "$$tscalar" = 'deny' ]; then \
			printf 'check:   %s is `task: deny`; no named allow expected, none required.\n' "$$f" >&2; \
		elif [ -z "$$tscalar" ] || [ "$$tscalar" = '{' ]; then \
			if [ "$$tpermn" -lt "$(MIN_TASK_ALLOWS)" ]; then \
				printf 'FAIL A7: extracted %d named task allow(s) from the task block of %s.\n' "$$tpermn" "$$f" >&2; \
				printf 'FAIL A7: expected an object-form `task:` block -- `"*": deny` first, then at least %d named allow(s). There is no `task:` key, or it has no entries. Refusing to compare an empty allowlist against the agent names.\n' "$(MIN_TASK_ALLOWS)" >&2; \
				fail=1; \
			fi; \
		fi; \
		if [ "$$tpermn" -gt 0 ] && [ "$$namesn" -gt 0 ]; then \
			unknown=$$(awk '$(AWK_NOT_IN)' "$$tmp/$$a.taskperm.txt" "$$tmp/agentnames.txt"); \
			if [ -n "$$unknown" ]; then \
				nameslist=$$(awk 'BEGIN { sep = "" } length($$0) > 0 { printf "%s%s", sep, $$0; sep = " " } END { print "" }' "$$tmp/agentnames.txt"); \
				printf 'FAIL A7: %s allows task to a name that is not a defined agent.\n' "$$f" >&2; \
				printf '      defined agents: %s\n' "$$nameslist" >&2; \
				printf '%s\n' "$$unknown" | sed 's/^/      inert allow: /' >&2; \
				printf 'FAIL A7: agent IDs are the frontmatter `name:`, case-sensitive: `Dispatcher` resolves and `dispatcher` does not. A misspelt name is a rule that can never match, so the agent is silently undispatchable with nothing reporting an error.\n' >&2; \
				fail=1; \
			fi; \
		fi; \
		xfirst=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  external_directory:[[:space:]]*$$/ { inb = 1; next } /^  external_directory:[[:space:]]*\{/ { inb = 1; next } inb && /^    [^[:space:]#]/ { s = $$0; sub(/^[[:space:]]*/, "", s); print s; exit }' "$$f"); \
		case "$$xfirst" in \
			'"*": '*|*'"*":'*) ;; \
			*) printf 'FAIL A8: %s external_directory block first key is `%s`.\n' "$$f" "$${xfirst:-<none>}" >&2; \
			   printf 'FAIL A8: expected: "*" first (e.g. "*": ask). A wildcard placed after a named rule shadows it under last-match-wins, so every credential path would resolve to ask -- a clickable prompt on ~/.aws/** instead of the hard block it is supposed to be.\n' >&2; \
			   fail=1 ;; \
		esac; \
		xperm=$$(awk '$(AWK_YAML_EXTDIR)' "$$f"); \
		printf '%s\n' "$$xperm" > "$$tmp/$$a.extdir.txt"; \
		xpermn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/$$a.extdir.txt"); \
		if [ "$$xpermn" -eq 0 ]; then \
			printf 'FAIL A8: extracted 0 rule(s) from the external_directory block of %s.\n' "$$f" >&2; \
			printf 'FAIL A8: expected an object-form `external_directory:` block -- `"*": ask` first, then the %d credential deny pattern(s). A bare `external_directory: ask` scalar, or no key at all, both extract nothing. Refusing to compare an empty block against the reference list.\n' "$(CREDENTIAL_DENIES_N)" >&2; \
			fail=1; \
		elif [ "$$xrefn" -gt 0 ] && ! diff -u "$$tmp/extdir.ref.txt" "$$tmp/$$a.extdir.txt" > "$$tmp/xd.txt" 2>&1; then \
			printf 'FAIL A8: the external_directory block of %s is not the expected rules in the expected order.\n' "$$f" >&2; \
			printf '      expected %d rule(s): "*": ask, then the credential denies in order. This block has %d. Difference:\n' "$$xrefn" "$$xpermn" >&2; \
			sed -n '/^@@/,$$p' "$$tmp/xd.txt" | sed 's/^/      /' >&2; \
			printf 'FAIL A8: every agent must declare this block identically and in order. A bare `"*": deny` catch-all lands after the global external_directory rules and wins them, which is what left every external path -- and every credential path -- hard-denied with no prompt; and a credential deny placed before the wildcard is shadowed by its own wildcard, which is worse.\n' >&2; \
			fail=1; \
		fi; \
		rfirst=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  read:[[:space:]]*$$/ { inb = 1; next } /^  read:[[:space:]]*\{/ { inb = 1; next } inb && /^    [^[:space:]#]/ { s = $$0; sub(/^[[:space:]]*/, "", s); print s; exit }' "$$f"); \
		case "$$rfirst" in \
			'"*": '*|*'"*":'*) ;; \
			*) printf 'FAIL A9: %s read block first key is `%s`.\n' "$$f" "$${rfirst:-<none>}" >&2; \
			   printf 'FAIL A9: expected: "*" first (e.g. "*": allow). The `.env` denies are appended after it on purpose; a wildcard placed after them would shadow every one of them.\n' >&2; \
			   fail=1 ;; \
		esac; \
		rperm=$$(awk '$(AWK_YAML_READ)' "$$f"); \
		printf '%s\n' "$$rperm" > "$$tmp/$$a.read.txt"; \
		rpermn=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/$$a.read.txt"); \
		if [ "$$rpermn" -lt "$(MIN_READ_RULES)" ]; then \
			printf 'FAIL A9: extracted %d rule(s) from the read block of %s.\n' "$$rpermn" "$$f" >&2; \
			printf 'FAIL A9: expected an object-form `read:` block -- `"*"` first, then at least %d rules including `*.env: deny` and `*.env.*: deny`. A bare `read: allow` scalar, or no key at all, both extract nothing. Refusing to assert against an empty block.\n' "$(MIN_READ_RULES)" >&2; \
			fail=1; \
		elif ! rord=$$(awk '$(AWK_READ_ORDER)' "$$tmp/$$a.read.txt") || [ -n "$$rord" ]; then \
			printf 'FAIL A9: the read block of %s does not deny `.env`, or a template allowance is ordered wrongly.\n' "$$f" >&2; \
			[ -n "$$rord" ] && printf '%s\n' "$$rord" >&2; \
			printf 'FAIL A9: opencode ships `*.env` as `ask`, not `deny` as the docs claim, and an agent-level `read: allow` is appended after it and wins -- a runtime probe returned a secret canary from a `.env`. And `*.env.*` matches `.env.example`, so under last-match-wins a template allow placed before it is inert and blocks a committed template.\n' >&2; \
			fail=1; \
		fi; \
		case " $(AGENTS_MIRROR) " in \
			*" $$a "*) ;; \
			*) continue ;; \
		esac; \
		afirst=$$(awk 'NR == 1 && $$0 == "---" { fm = 1; next } NR == 1 { fm = 0 } fm && $$0 == "---" { fm = 0; next } !fm { next } /^  bash:[[:space:]]*$$/ { inb = 1; next } inb && /^  [^[:space:]#]/ { inb = 0 } inb && /^    [^[:space:]#]/ { s = $$0; sub(/^[[:space:]]*/, "", s); print; exit }' "$$f"); \
		case "$$afirst" in \
			'"*": '*|*'"*":'*) ;; \
			*) printf 'FAIL A2: %s object-form bash block first key is `%s`.\n' "$$f" "$${afirst:-<none>}" >&2; \
			   printf 'FAIL A2: expected: "*" first (e.g. "*": allow). Any earlier deny is shadowed by the wildcard under last-match-wins.\n' >&2; \
			   fail=1 ;; \
		esac; \
		agent=$$(awk '$(AWK_YAML_BASH)' "$$f"); \
		printf '%s\n' "$$agent" > "$$tmp/$$a.txt"; \
		acount=$$(awk 'length($$0) > 0 { c++ } END { print c + 0 }' "$$tmp/$$a.txt"); \
		if [ "$$acount" -eq 0 ]; then \
			printf 'FAIL A3: extracted 0 deny patterns from %s.\n' "$$f" >&2; \
			printf 'FAIL A3: expected at least %d mirroring opencode.json. Refusing to compare an empty agent list against anything.\n' "$(MIN_DENY)" >&2; \
			fail=1; continue; \
		fi; \
		if [ "$$acount" -lt "$(MIN_DENY)" ]; then \
			printf 'FAIL A3: %s has %d deny pattern(s), expected at least %d.\n' "$$f" "$$acount" "$(MIN_DENY)" >&2; \
			fail=1; \
		fi; \
		if ! diff -u "$$tmp/global.txt" "$$tmp/$$a.txt" > "$$tmp/d.txt" 2>&1; then \
			printf 'FAIL A3: deny patterns in %s do not match opencode.json permission.bash in order.\n' "$$f" >&2; \
			printf '      expected %d pattern(s) from opencode.json, in that order. Difference:\n' "$$gcount" >&2; \
			sed -n '/^@@/,$$p' "$$tmp/d.txt" | sed 's/^/      /' >&2; \
			fail=1; \
		fi; \
	done; \
	if [ "$$fail" -ne 0 ]; then \
		printf 'check: FAILED\n' >&2; \
		exit 1; \
	fi; \
	printf 'check: OK — bash deny-list, permission ordering, skill scope, task scope, external_directory and .env ordering consistent across opencode.json and agent/*.md\n'
endef

.PHONY: deploy reinstall clean check help eval eval-static eval-behavior \
        eval-selftest

## check: assert permission consistency; installs nothing
check:
	$(CHECK_CMDS)

## deploy: non-destructive install (default target)
#
# `check` is an explicit prerequisite rather than an extra recipe step: it must
# pass before anything is copied, so a drifting tree is never installed.
# `deploy` and `reinstall` invoke the SAME CHECK_CMDS block, so the two can never
# disagree about whether the tree is valid.
deploy: check
	$(REQUIRE_DEST)
	$(COPY_CMDS)

## reinstall: wipe managed files, then deploy from scratch
#
# Guard + remove + copy are explicit sequential recipe steps on purpose: a
# `reinstall: clean check copy` prerequisite pair would be order-dependent and
# could race under `make -j`, letting the copy and the removal interleave, or
# letting the copy happen before `check` had already failed the build.
reinstall: check
	$(REQUIRE_DEST)
	$(REQUIRE_OPENCODE_DIR)
	$(CLEAN_CMDS)
	$(COPY_CMDS)

## clean: remove only agent/, skills/ and opencode.json from $(DEST)
clean:
	$(REQUIRE_DEST)
	$(REQUIRE_OPENCODE_DIR)
	$(CLEAN_CMDS)

# =============================================================================
# Behavioural evaluation harness (eval/)
# =============================================================================
#
# Two tiers, deliberately unequal, and the split is the whole design:
#
#   eval-static   deterministic, offline, free. Derives assertions from the
#                 rule array V1 actually resolves (`opencode debug agent`) plus
#                 file content, and is the DEFAULT gate. Exits non-zero on any
#                 failure.
#   eval-behavior real model calls, non-deterministic, costly. Reports a pass
#                 RATE over N runs and prints every individual run. Refuses to
#                 run without EVAL_CONFIRM=1 and prints a cost estimate first.
#                 NOT a gate -- see eval/README.md for the measured flake rate.
#
# `check` stays the prerequisite of both, exactly as it is for `deploy`. It is
# not weakened, reordered, or bypassed: the static tier adds assertions `check`
# does not make (resolved-array scope, bash deny resolution, credential paths,
# frontmatter-name resolution, deploy equivalence) rather than restating A1-A6.
# A single `check` prerequisite cannot race under `make -j` because there is no
# second parallel branch to interleave with.
#
# Isolation is structural, not a convention: every target builds a throwaway
# HOME under $TMPDIR, copies the repo (with .git) into it, and points opencode
# at that. `eval_static.py` and `eval_behavior.py` both fingerprint the
# operator's real ~/.config/opencode before and after and fail if a single byte
# or mtime moved. The evaluated agents never have the live repo as their cwd.
#
# python3 appears here and only here. `check` stays free of it, as it was
# before this section existed -- no jq, no test framework, no package manager.
# Overridable with EVAL_PYTHON=... if the default interpreter is unsuitable.
# =============================================================================

EVAL_PYTHON ?= python3
EVAL_DIR    := $(SRC)/eval

## eval: run the default tier (alias for eval-static)
eval: eval-static

## eval-static: tier 1 -- deterministic config-derived assertions
eval-static: check
	@command -v $(EVAL_PYTHON) >/dev/null 2>&1 || { \
		printf 'error: %s not found; set EVAL_PYTHON to a python3 interpreter.\n' '$(EVAL_PYTHON)' >&2; \
		exit 1; \
	}
	$(EVAL_PYTHON) "$(EVAL_DIR)/static/eval_static.py" --repo "$(SRC)"

## eval-behavior: tier 2 -- real model calls, opt-in, reports a pass RATE
#
# Prints an estimated cost and refuses to spend anything until EVAL_CONFIRM=1.
#   make eval-behavior EVAL_CONFIRM=1
#   make eval-behavior EVAL_CONFIRM=1 EVAL_RUNS=5
#   make eval-behavior EVAL_CONFIRM=1 CASE=B1-delegation-gate
eval-behavior: check
	@printf 'eval-behavior makes real model calls and is NON-DETERMINISTIC.\n'
	@printf 'It reports a pass rate and is NOT a gate. Cost is estimated below.\n'
	@$(EVAL_PYTHON) "$(EVAL_DIR)/behavior/eval_behavior.py" \
		--repo "$(SRC)" \
		$(if $(CASE),--case "$(CASE)",) \
		$(if $(RUNS),--runs $(RUNS),)

## eval-selftest: prove the static tier can actually fail
#
# A harness that has never gone red is indistinguishable from one that passes
# vacuously. This target makes seven targeted defects in a scratch COPY of the
# repo -- never in the working tree -- and requires the tier that owns each one
# to catch it. The third one flips a deny in all four files at once, which
# `make check` accepts; it is here specifically to show the static tier catches
# what the text-level gate structurally cannot. The last four are the seeds for
# the assertions that live in `check` rather than in the static tier: a bare
# `task: allow` (M4), a task allow whose name is spelled in the wrong case --
# a rule the runtime can never match (M5) -- and the two ordering defects A8
# and A9 were added for: a credential deny missing from one agent's
# external_directory block (M6) and a `.env` template allow placed where
# `*.env.*: deny` shadows it (M7).
eval-selftest: check
	@printf 'eval-selftest: mutating a scratch copy under $${TMPDIR:-/tmp}, not the working tree\n'
	@$(EVAL_PYTHON) "$(EVAL_DIR)/selftest/eval_selftest.py" --repo "$(SRC)"

## help: list available targets
help:
	@printf 'opencode-harness — available targets:\n\n'
	@printf '  %-14s %s\n' 'deploy'         'non-destructive install into $(DEST) (default)'
	@printf '  %-14s %s\n' 'reinstall'      'destructive: remove agent/, skills/, opencode.json then deploy'
	@printf '  %-14s %s\n' 'clean'          'destructive: remove agent/, skills/, opencode.json only'
	@printf '  %-14s %s\n' 'check'          'assert permission consistency (also run by deploy/reinstall)'
	@printf '  %-14s %s\n' 'eval'           'run the eval harness default tier (== eval-static)'
	@printf '  %-14s %s\n' 'eval-static'    'tier 1: deterministic config-derived assertions (the gate)'
	@printf '  %-14s %s\n' 'eval-selftest'  'prove the gates fail on seven seeded defects'
	@printf '  %-14s %s\n' 'eval-behavior'  'tier 2: real model calls, opt-in, reports a pass RATE'
	@printf '  %-14s %s\n' 'help'           'show this message'
	@printf '\ncurrent DEST = %s\n' '$(DEST)'
	@printf 'override with: make DEST=/tmp/opencode-deploy-test deploy\n'
	@printf '\neval tier 2 needs an explicit confirmation and spends real model calls:\n'
	@printf '  make eval-behavior EVAL_CONFIRM=1 [EVAL_RUNS=3] [CASE=<id>]\n'