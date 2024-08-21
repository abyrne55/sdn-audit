#!/bin/bash
set -euo pipefail

REASON="${REASON:-sdn-audit}"

if [ "$#" -ne 2 ]; then
    echo "error: incorrect number of arguments"
    echo "usage: $0 CID_FILE OUTPUT_DIR"
    echo "CID_FILE is th epath to a list of internal cluster IDs, one per line, ending with a newline"
    echo "OUTPUT_DIR is an existing directory where output from the audit commands will be written"
    exit 1
fi

while read CID; do
    OUT="$2/$CID"
    if [ -d $OUT ]; then
        echo "Skipping $CID because $OUT exists"
    else
        echo $CID

        # Log into the cluster
        ocm backplane login $CID || continue

	mkdir $OUT
        set +e
        # Describe the network operator resource (will be parsed by audit.py)
        oc get network.operator cluster -o json > $OUT/network.operator.json

        # Test a few key resources for certain conditions. We unset/set the 'e' flag here because
        # these commands are expected to return error codes in many normal situations
        oc get hostsubnet -o yaml 2>/dev/null | grep egressCIDRs 1> $OUT/egress_cidrs
        oc get netnamespace -o yaml 2>/dev/null | grep 'netnamespace.network.openshift.io/multicast-enabled=true' 1> $OUT/multicast
        ocm backplane elevate "$REASON" -- get EgressNetworkPolicy -A 1> $OUT/egress_network_policy 2>/dev/null
        set -e
    fi
    
done < $1
