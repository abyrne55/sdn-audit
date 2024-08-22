#!/bin/bash
set -euo pipefail

REASON="${REASON:-sdn-audit}"
TIMEOUT="timeout -v -s INT -k 2s 9s"

if [ "$#" -ne 2 ]; then
    echo "error: incorrect number of arguments"
    echo "usage: $0 CID_FILE OUTPUT_DIR"
    echo "CID_FILE is th epath to a list of internal cluster IDs, one per line, ending with a newline"
    echo "OUTPUT_DIR is an existing directory where output from the audit commands will be written"
    exit 1
fi

while read CID; do
    OUT="$2/$CID"

    # Skip this cluster entirely if we already have the 5 files this loop generates
    if [ $(ls -1 $OUT 2>/dev/null | wc -l) -eq 5 ]; then
        echo Skipping $CID
        continue
    fi
    echo $CID

    # Log into the cluster
    ocm backplane login $CID || continue

    # Make the output directory
    mkdir -p $OUT

    # We unset/set the 'e' flag here because these commands are expected to return 
    # error codes in many normal situations
    set +e
    # Describe the nodes and network operator resources (will be parsed by audit.py)
    [ -f $OUT/nodes.json ] || $TIMEOUT oc get nodes -o json > $OUT/nodes.json
    [ -f $OUT/network.operator.json ] || $TIMEOUT oc get network.operator cluster -o json > $OUT/network.operator.json

    # Test a few key resources for certain conditions. 
    [ -f $OUT/egress_cidrs ] || $TIMEOUT oc get hostsubnet -o yaml 2>/dev/null | grep egressCIDRs 1> $OUT/egress_cidrs
    [ -f $OUT/multicast ] || $TIMEOUT oc get netnamespace -o yaml 2>/dev/null | grep 'netnamespace.network.openshift.io/multicast-enabled=true' 1> $OUT/multicast
    [ -f $OUT/egress_network_policy ] || $TIMEOUT ocm backplane elevate "$REASON" -- get EgressNetworkPolicy -A 1> $OUT/egress_network_policy 2>/dev/null
    set -e
done < $1
