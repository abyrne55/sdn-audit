import json
import os
import pathlib
import re
from ocm import OCMClient


def describe_ocm_cluster(ocm: OCMClient, cluster_id: str) -> dict:
    """Queries OCM and returns a dict of key cluster stats"""
    cluster = ocm.get("/api/clusters_mgmt/v1/clusters/" + cluster_id).json()
    subscription = ocm.get(cluster["subscription"]["href"]).json()
    org_id = subscription["organization_id"]
    org_name = ocm.get("/api/accounts_mgmt/v1/organizations/" + org_id).json()["name"]

    try:
        compute_machine_type_cpus = machine_type_cpu_qty(
            ocm, cluster["nodes"]["compute_machine_type"]["id"]
        )
    except KeyError:
        compute_machine_type_cpus = -1

    try:
        compute_nodes = cluster["nodes"]["compute"]
        total_nodes = (
            cluster["nodes"]["master"] + cluster["nodes"]["infra"] + compute_nodes
        )
        compute_vcpu_max = compute_machine_type_cpus * compute_nodes
    except KeyError:
        max_replicas = cluster["nodes"]["autoscale_compute"]["max_replicas"]
        total_nodes = (
            cluster["nodes"]["master"] + cluster["nodes"]["infra"] + max_replicas
        )
        compute_nodes = (
            f"{cluster['nodes']['autoscale_compute']['min_replicas']}-{max_replicas}"
        )
        compute_vcpu_max = compute_machine_type_cpus * max_replicas

    try:
        local_zones = uses_local_zones(ocm, cluster["machine_pools"]["href"])
    except KeyError:
        local_zones = "?"

    return {
        "org_name": org_name,
        "cid": cluster["id"],
        "name": cluster["name"],
        "product": cluster["product"]["id"],
        "cloud": cluster["cloud_provider"]["id"],
        "region": cluster["region"]["id"],
        "version": cluster["openshift_version"],
        "state": cluster["state"],
        "network": cluster["network"]["type"],
        "total_nodes": total_nodes,
        "compute_nodes": compute_nodes,
        "compute_vcpu_max": compute_vcpu_max,
        "fips": cluster["fips"] if "fips" in cluster else False,
        "proxy": (len(cluster["proxy"]) > 0) if "proxy" in cluster else False,
        "multi_az": cluster["multi_az"],
        "local_zones": local_zones,
        "limited_support": (cluster["status"]["limited_support_reason_count"] > 0),
    }


def parse_network_operator_spec(cid_audit_dir: str, expected_cni=None) -> dict:
    """
    Returns a dictionary of info extracted from the network operator JSON spec
    contained within on-cluster-audit results, optionally with a sanity check of
    the expected CNI (raises ArithmeticError if expectation not met)
    """
    network_operator_path = os.path.join(cid_audit_dir, "network.operator.json")
    with open(network_operator_path, encoding="UTF-8") as f:
        net_spec = json.load(f)["spec"]
        cni = net_spec["defaultNetwork"]["type"]
        if expected_cni is not None and cni != expected_cni:
            raise ArithmeticError(
                f"expected CNI {expected_cni} but cluster thinks its CNI is {cni}"
            )
        audit_res = {
            "mtu": "?",
            "tunnel_port": "?",
            "multitenant": "?",
            "local_gateway": "?",
        }
        try:
            if cni == "OpenShiftSDN":
                sdn_cfg = net_spec["defaultNetwork"]["openshiftSDNConfig"]
                audit_res["mtu"] = sdn_cfg["mtu"]
                audit_res["tunnel_port"] = sdn_cfg["vxlanPort"]
                audit_res["multitenant"] = sdn_cfg["mode"] == "Multitenant"
                audit_res["local_gateway"] = "n/a"
            if cni == "OVNKubernetes":
                ovn_cfg = net_spec["defaultNetwork"]["ovnKubernetesConfig"]
                audit_res["mtu"] = ovn_cfg["mtu"]
                audit_res["tunnel_port"] = ovn_cfg["genevePort"]
                audit_res["multitenant"] = "n/a"
                audit_res["local_gateway"] = ovn_cfg["gatewayConfig"]["routingViaHost"]
        except KeyError as exc:
            print(f"WARN: {network_operator_path} missing expected key {exc}")
    return audit_res


def machine_type_cpu_qty(ocm: OCMClient, machine_type: str) -> int:
    """Returns the number of vCPUs present in a given machine type"""
    return ocm.get("/api/clusters_mgmt/v1/machine_types/" + machine_type).json()["cpu"][
        "value"
    ]


def file_not_empty(dir_path: str, file_name: str) -> bool:
    """
    Returns true if a file exists and has more than just whitespace. Raises
    OSError if file does not exist
    """
    p = pathlib.Path(os.path.join(dir_path, file_name))
    return not is_nully_str(p.read_text(encoding="UTF-8"))


def is_nully_str(s):
    """
    Returns True if s is None, an empty or whitespace-filled string, or some variation of "NULL"
    """
    if s is None:
        return True
    s_strip = s.lower().strip()
    return s_strip in ["", "null"]


def uses_local_zones(ocm: OCMClient, machine_pools_href: str) -> bool:
    """
    Returns true if the cluster has a machine pool in an AWS Local Zone. Raises KeyError on some
    older clusters for which machine pools are not marked with their AZs
    """
    re_local_zone = re.compile(r"[a-z]+-[a-z]+-[\d]-[a-z]+-[a-z\d]+")
    azs = [
        az
        for mp in ocm.get(machine_pools_href).json()["items"]
        for az in mp["availability_zones"]
    ]
    return any(map(re_local_zone.fullmatch, azs))
