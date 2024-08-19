from util import OCMClient

def describe_ocm_cluster(ocm: OCMClient, cluster_id: str) -> dict:
    """Queries OCM and returns a dict of key cluster stats"""
    cluster = ocm.get("/api/clusters_mgmt/v1/clusters/" + cluster_id).json()
    subscription = ocm.get(cluster['subscription']['href']).json()
    org_id = subscription['organization_id']
    compute_machine_type = machine_type_cpu_qty(ocm, cluster['nodes']['compute_machine_type']['id'])
    try:
        compute_nodes = cluster['nodes']['compute']
        total_nodes = cluster['nodes']['master'] + cluster['nodes']['infra'] + compute_nodes
        compute_vcpu_max = compute_machine_type * compute_nodes
    except KeyError:
        max_replicas = cluster['nodes']['autoscale_compute']['max_replicas']
        total_nodes = cluster['nodes']['master'] + cluster['nodes']['infra'] + max_replicas
        compute_nodes = f"{cluster['nodes']['autoscale_compute']['min_replicas']}-{max_replicas}"
        compute_vcpu_max = compute_machine_type * max_replicas
    org_name = ocm.get("/api/accounts_mgmt/v1/organizations/" + org_id).json()['name']
    return {
        'org_name': org_name,
        'cid': cluster['id'],
        'name': cluster['name'],
        'product': cluster['product']['id'],
        'cloud': cluster['cloud_provider']['id'],
        'region': cluster['region']['id'],
        'version': cluster['openshift_version'],
        'state': cluster['state'],
        'network': cluster['network']['type'],
        'total_nodes': total_nodes,
        'compute_nodes': compute_nodes,
        'compute_vcpu_max': compute_vcpu_max,
        'fips': cluster['fips'] if 'fips' in cluster else False,
        'multi_az': cluster['multi_az'],
        'limited_support': (cluster['status']['limited_support_reason_count'] > 0),
    }

def machine_type_cpu_qty(ocm: OCMClient, machine_type: str) -> int:
    """Returns the number of vCPUs present in a given machine type"""
    return ocm.get("/api/clusters_mgmt/v1/machine_types/"+machine_type).json()['cpu']['value']
