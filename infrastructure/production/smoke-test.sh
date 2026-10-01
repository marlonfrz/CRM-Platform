#!/bin/sh
set -eu

public_url=${1:?Usage: smoke-test.sh https://crm.example.com}
public_url=${public_url%/}

curl --fail --silent --show-error "$public_url/api/health" > /dev/null
curl --fail --silent --show-error --location "$public_url/login" > /dev/null
printf 'Production smoke test passed for %s\n' "$public_url"
