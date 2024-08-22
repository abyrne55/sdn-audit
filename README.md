# sdn-audit
Scripts for auditing the SDN and OVN networks of a fleet of OpenShift clusters 

## Prerequisites
* Bash
* Python 3.12 (although it might work as far back as 3.9?)
* All the pip packages in requirements.txt (run `pip3 install -r requirements.txt`)

## Usage
### Step 1: Preparing the CID list
First, prepare the list of internal cluster IDs you'd like to audit. You might consider using the [OCM CLI](https://github.com/openshift-online/ocm-cli) to do this, e.g.,
```sh
ocm list clusters --managed --parameter search="state is 'ready' and hypershift.enabled is not 'true'" --columns=id --no-headers > cluster_ids.txt
```
Regardless of how you generate it, ensure that your input file consists of one internal cluster ID per line and has a single terminating newline.

### Step 2: Running the on-cluster audit (optional)
> [!NOTE]  
> This step will take about 10-20 seconds per cluster in your input file. The script is designed to handle most `oc` errors on its own and keep going, but if it doesn't, you can just run the script again and it will automatically skip any clusters for which it has already gathered the necessary data.

Ensure that you're logged into OCM (`ocm login --use-auth-code`). Designate an empty directory as your "on-cluster audit results" directory, and then run the included `on_cluster_audit.sh` Bash script. This script will log into clusters via [Backplane](https://github.com/openshift/backplane-cli) and run a handful of commands to gather some basic information about cluster networking. Since one of these commands requires elevated privileges, you'll probably want to set the REASON env-var, e.g., 
```sh
REASON="an important audit" ./on_cluster_audit.sh ./cluster_ids.txt ./on_cluster_audits_dir
```

This step is technically optional because `audit.py` (the next step) can still generate an output CSV without looking at any on-cluster audit results. You just won't get as much useful info.

### Step 3: Filling in gaps with OCM data
Once your on-cluster audit finishes (if applicable), ensure (again) that you're logged into OCM (`ocm login --use-auth-code`), and use the included `audit.py` script to generate a CSV report.
```
./audit.py ./cluster_ids.txt report.csv --on-cluster-audit-dir ./on_cluster_audits_dir
```
See `./audit.py -h` for more options