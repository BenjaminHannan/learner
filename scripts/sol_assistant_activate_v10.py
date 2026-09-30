#!/usr/bin/env python3
"""Explicit durable activation/rollback for exact verified ordered bundles."""
import argparse,json
from sol_assistant_candidate_pointer_v10 import BundlePointer
from sol_assistant_ordered_bundle_v10 import verify
from sol_assistant_night_bundle_v10 import check_pointer_decision

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True)
    sub=p.add_subparsers(dest='action',required=True)
    init=sub.add_parser('initialize');init.add_argument('--bundle',required=True)
    accept=sub.add_parser('accept');accept.add_argument('--bundle',required=True);accept.add_argument('--decision',required=True);accept.add_argument('--decision-sha256',required=True);accept.add_argument('--revision',type=int,required=True)
    rollback=sub.add_parser('rollback');rollback.add_argument('--revision',type=int,required=True)
    sub.add_parser('current');a=p.parse_args();pointer=BundlePointer(a.state)
    if a.action=='initialize':r=pointer.initialize(a.bundle,check_bundle=verify)
    elif a.action=='accept':r=pointer.accept(a.bundle,expected_revision=a.revision,decision_path=a.decision,trusted_decision_sha256=a.decision_sha256,check_bundle=verify,check_decision=check_pointer_decision)
    elif a.action=='rollback':r=pointer.rollback(expected_revision=a.revision,check_bundle=verify)
    else:r=pointer.current(check_bundle=verify)
    print(json.dumps({k:v for k,v in r.items() if k!='checked'},indent=2))
if __name__=='__main__':main()
