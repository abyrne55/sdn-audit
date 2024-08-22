#!/usr/bin/env python3
import argparse
import csv
import os
import time
from requests_cache import install_cache, NEVER_EXPIRE
from requests import exceptions as req_exceptions

# Enable HTTP caching globally before importing network-using modules
install_cache(
    ".ocm-http-cache",
    backend="sqlite",
    expire_after=NEVER_EXPIRE,
    allowable_methods=["GET"],
)
# pylint: disable=wrong-import-position, C0103
from ocm import OCMClient
from data import describe_ocm_cluster, parse_network_operator_spec, file_not_empty

# Parse command line arguments
arg_parser = argparse.ArgumentParser(
    description="Audit the network configurations of managed OpenShift clusters"
)
# argparse will call open() on csv_file automatically (no need to use "with open(...) as f")
arg_parser.add_argument(
    "cid_file",
    type=argparse.FileType(mode="r"),
    help="path to a list of internal cluster IDs, one per line",
)
arg_parser.add_argument(
    "csv_file",
    action="store",
    help="output path for the CSV containing audit results (see also -a, -c)",
)
arg_parser.add_argument(
    "--on-cluster-audit-dir",
    action="store",
    metavar="PATH",
    help="optional path to directory where on-cluster audit results are stored, organized by cluster ID",
)
arg_parser.add_argument(
    "-n",
    "--no-headers",
    action="store_true",
    help="skip writing headers to output CSV file (see also -a)",
)
arg_parser.add_argument(
    "-a",
    "--append",
    action="store_true",
    help="append to CSV output file instead of overwriting it (cannot be used with -c)",
)
arg_parser.add_argument(
    "-c",
    "--clobber",
    action="store_true",
    help="overwrite output CSV file if it already exists (cannot be used with -a)",
)
args = arg_parser.parse_args()

# Fetch data for each cluster ID in the cid_file
ocm = OCMClient()
csv_rows = []
for cid in args.cid_file:
    try:
        csv_rows.append(describe_ocm_cluster(ocm, cid.strip()))
    except req_exceptions.ConnectionError as exc:
        print(f"WARN: Retrying {cid.strip()} in 5s due to {exc}")
        time.sleep(5)
        try:
            csv_rows.append(describe_ocm_cluster(ocm, cid.strip()))
        except Exception as exc2:
            print(f"ERR: failed to handle {cid.strip()}: {exc2}")
    except KeyError as exc:
        print(f"ERR: failed to handle {cid.strip()} due to missing data in OCM: {exc}")
#csv_rows = [describe_ocm_cluster(ocm, cid.strip()) for cid in args.cid_file]
args.cid_file.close()

if args.on_cluster_audit_dir:
    for i, row in enumerate(csv_rows):
        cid_audit_dir = os.path.join(args.on_cluster_audit_dir, row["cid"])
        try:
            csv_rows[i] = row | parse_network_operator_spec(
                cid_audit_dir, row["network"]
            )
        except OSError as exc:
            print(
                f"WARN: failed to parse network operator spec from {cid_audit_dir}: {exc}"
            )
        except ArithmeticError as exc:
            print(
                f"ERR: LOOK INTO {cid.strip()}: {exc}"
            )

        for metric in ["egress_network_policy", "egress_cidrs", "multicast"]:
            try:
                csv_rows[i][metric] = file_not_empty(cid_audit_dir, metric)
            except OSError as exc:
                print(f"WARN: failed to parse {metric} from {cid_audit_dir}: {exc}")
                csv_rows[i][metric] = "?"

# Write rows to output CSV
access_mode = "x"
if args.clobber:
    access_mode = "w"
if args.append:
    access_mode = "a"
with open(args.csv_file, access_mode, encoding="UTF-8") as csv_file:
    column_names = csv_rows[0].keys()
    csv_writer = csv.DictWriter(csv_file, column_names)
    if not args.no_headers:
        csv_writer.writeheader()
    csv_writer.writerows(csv_rows)
