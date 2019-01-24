# spa envs
SPA_CONFIG                  ?= spa.local_settings
SPA_DEBUG_LOG               ?= /tmp/debug.log

PYTHONPATH                  := ${PWD}:${PYTHONPATH}
PYTHONDONTWRITEBYTECODE      = 1

export

define HELP_OUTPUT
Available targets:
  help                this help
  clean               clean up
  debug               run without daemon in development mode
endef
export HELP_OUTPUT

.PHONY: help clean debug

help:
	@echo "$$HELP_OUTPUT"

clean:
	@echo "--- cleaning"
	@echo "cleaning debug.log"
	@rm -f debug.log
	@echo "cleaning *.pyc, __pycache__, and empty dirs"
	@(for d in spa; do \
      find "$${d}" -type f -name "*.pyc" -delete; \
      find "$${d}" -type d -name "__pycache__" -delete; \
      find "$${d}" -mindepth 1 -type d -empty -delete; \
      done)

debug:
	@python spa/server.py debug
