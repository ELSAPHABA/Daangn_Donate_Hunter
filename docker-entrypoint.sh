#!/bin/sh
set -eu

: "${TZ:=UTC}"
: "${DATA_DIR:=/data}"
: "${USER_ACTIVITY_LOG:=${DATA_DIR}/user_activity.log}"
: "${ERROR_LOG:=${DATA_DIR}/error.log}"

export TZ DATA_DIR USER_ACTIVITY_LOG ERROR_LOG

mkdir -p "$DATA_DIR"
mkdir -p "$(dirname "$USER_ACTIVITY_LOG")" "$(dirname "$ERROR_LOG")"
touch "$USER_ACTIVITY_LOG" "$ERROR_LOG"

if [ "$#" -eq 0 ]; then
  set -- bot
fi

exec daangn-donate-hunter "$@"
