#!/usr/bin/env bash
# Compatibilidade: a implementação canônica fica em scripts/deploy/lib.sh.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../scripts/deploy/lib.sh
source "$ROOT/scripts/deploy/lib.sh"
