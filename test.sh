#!/bin/sh
P_ID=$1
echo "current p_id: ${P_ID}" >&2
P_ID=$((P_ID + 1))
echo "${P_ID}"