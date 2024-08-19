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
    echo $CID
    ocm backplane login $CID
    OUT="$2/$CID"
    mkdir -p $OUT
    oc get network.operator cluster -o json > $OUT/network.operator.json
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.type}' > $OUT/cni_type
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.openshiftSDNConfig.mtu}' > $OUT/sdn_mtu
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.ovnKubernetesConfig.mtu}' > $OUT/ovn_mtu
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.openshiftSDNConfig.vxlanPort}' > $OUT/sdn_tunnel_port
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.ovnKubernetesConfig.genevePort}' > $OUT/ovn_tunnel_port
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.ovnKubernetesConfig.gatewayConfig.routingViaHost}' > $OUT/local_gateway_mode
    # oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.openshiftSDNConfig.mode}' > $OUT/multitenant
    set +e
    ocm backplane elevate "$REASON" -- get EgressNetworkPolicy -A 1> $OUT/egress_network_policy 2>/dev/null
    oc get hostsubnet -o yaml 2>/dev/null | grep egressCIDRs 1> $OUT/egress_cidrs
    oc get netnamespace -o yaml 2>/dev/null | grep 'netnamespace.network.openshift.io/multicast-enabled=true' 1> $OUT/multicast
    set -e
    
done < $1