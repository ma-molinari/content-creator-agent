#!/bin/sh
set -eu

if ! awslocal s3api head-bucket --bucket postmind-local >/dev/null 2>&1; then
  awslocal s3api create-bucket --bucket postmind-local >/dev/null
fi
