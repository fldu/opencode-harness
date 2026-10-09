# =============================================================================
# opencode-harness — install agents & skills into the global opencode config
# =============================================================================
#
# Usage:
#   make                 # same as `make deploy` (deploy is the default target)
#   make deploy          # non-destructive install (overwrites same-named files)
#   make reinstall       # destructive: wipe agent/, skills/, opencode.json, then
#                        # a fresh deploy
#   make clean           # destructive: remove agent/, skills/, opencode.json only
#   make help            # list targets
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

.PHONY: deploy reinstall clean help

## deploy: non-destructive install (default target)
deploy:
	$(REQUIRE_DEST)
	$(COPY_CMDS)

## reinstall: wipe managed files, then deploy from scratch
#
# Guard + remove + copy are explicit sequential recipe steps on purpose: a
# `reinstall: clean copy` prerequisite pair would be order-dependent and could
# race under `make -j`, letting the copy and the removal interleave.
reinstall:
	$(REQUIRE_DEST)
	$(REQUIRE_OPENCODE_DIR)
	$(CLEAN_CMDS)
	$(COPY_CMDS)

## clean: remove only agent/, skills/ and opencode.json from $(DEST)
clean:
	$(REQUIRE_DEST)
	$(REQUIRE_OPENCODE_DIR)
	$(CLEAN_CMDS)

## help: list available targets
help:
	@printf 'opencode-harness — available targets:\n\n'
	@printf '  %-10s %s\n' 'deploy'    'non-destructive install into $(DEST) (default)'
	@printf '  %-10s %s\n' 'reinstall' 'destructive: remove agent/, skills/, opencode.json then deploy'
	@printf '  %-10s %s\n' 'clean'     'destructive: remove agent/, skills/, opencode.json only'
	@printf '  %-10s %s\n' 'help'      'show this message'
	@printf '\ncurrent DEST = %s\n' '$(DEST)'
	@printf 'override with: make DEST=/tmp/opencode-deploy-test deploy\n'