#!/bin/bash
BASH_DIR=$(dirname $(realpath "${BASH_SOURCE}"))

rm ${BASH_DIR}/../cloudflare-ddns-manager.tar.gz

docker buildx build --platform linux/amd64 --tag cloudflare-ddns-manager:latest ${BASH_DIR}/../ --load
# TODO: Support linux/riscv64
docker save cloudflare-ddns-manager:latest > cloudflare-ddns-manager.tar.gz