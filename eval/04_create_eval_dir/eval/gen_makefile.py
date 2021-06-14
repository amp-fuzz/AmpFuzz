#!/usr/bin/env python3
# coding: utf-8

import json
import os

with open('package_matches.json') as f:
    packages = json.load(f)

if os.path.exists('final_eval.json'):
    with open('final_eval.json') as f:
        final_eval = set(tuple(x) for x in json.load(f))
else:
    final_eval = set()

pkg_rules = []
target_rules = []
fuzz_prep_rules = []
fuzz_prep_targets_final = []
fuzz_rules = []
fuzz_targets_final = []
sym_prep_rules = []
sym_prep_targets_final = []
sym_rules = []
honey_syn_rules = []

ex_timeout=10
sym_targets_final = []

for pkg, pkg_info in sorted(packages.items()):
    version = pkg_info['version']
    # add package-specific rules'
    base_slug = "base"
    base_iid_file = f"{pkg}/.{base_slug}.iid"
    pkg_rules.append((base_iid_file,
                      [],
                      [f"mkdir -p {pkg}",
                       f"bash build_base.sh {pkg} \"{version}\" $@ > {pkg}/build_{base_slug}.log 2>&1"]))

    binaries = pkg_info['binaries']
    for binary, ports in sorted(binaries.items()):
        # add target-specific rules
        target_name = binary.replace('/', '_')
        target_slug = f"{target_name}"
        target_iid_file = f"{pkg}/.{target_slug}.iid"
        target_rules.append((target_iid_file,
                             [base_iid_file],
                             [
                                 f"bash build_target.sh {base_iid_file} {binary} $@ > {pkg}/build_{target_slug}.log 2>&1"]))

        for port in sorted(ports):
            # add fuzzing-specific rules
            fuzz_slug = f"fuzz_{target_slug}_{port}"
            fuzz_iid_file = f"{pkg}/.{fuzz_slug}.iid"
            fuzz_prep_rules.append((fuzz_iid_file,
                                    [target_iid_file],
                                    [
                                        f"bash build_fuzz.sh {target_iid_file} {pkg} {binary} {port} $@ > {pkg}/build_{fuzz_slug}.log 2>&1"]))

            fuzz_log = f"{pkg}/{fuzz_slug}.log"
            fuzz_out = f"{pkg}/{fuzz_slug}"
            fuzz_cid = f"{pkg}/.{fuzz_slug}.cid"
            fuzz_rules.append((f"{fuzz_log} {fuzz_out}",
                               [fuzz_iid_file],
                               [
                                   f"-docker run --cpu-quota=200000 --cidfile {fuzz_cid} $$(cat {fuzz_iid_file}) timeout ${{TIMEOUT}} /fuzz.sh >{fuzz_log} 2>&1",
                                   f"-docker cp $$(cat {fuzz_cid}):{binary}.out {fuzz_out}"]))

            # add symbolic execution-specific rules
            sym_slug = f"sym_{target_slug}_{port}"
            sym_iid_file = f"{pkg}/.{sym_slug}.iid"
            sym_prep_rules.append((sym_iid_file,
                                   [target_iid_file, f"{fuzz_out}"],
                                   [
                                       f"bash build_sym.sh {target_iid_file} {pkg} {binary} {port} $@ > {pkg}/build_{sym_slug}.log 2>&1"]))

            sym_log = f"{pkg}/{sym_slug}.log"
            sym_cid = f"{pkg}/.{sym_slug}.cid"
            sym_rules.append((sym_log,
                               [sym_iid_file],
                               [f"-docker run --env EX_TIMEOUT={ex_timeout} --cidfile {sym_cid} $$(cat {sym_iid_file}) /sym.sh >{sym_log} 2>&1",
                                f"-docker cp $$(cat {sym_cid}):{binary}.sym.result {pkg}/{sym_slug}"]))
            # add honeypot code synthesis-specific rules
            honey_syn_slug = f"honey_syn_{target_slug}_{port}"
            honey_syn_iid_file = f"{pkg}/.{honey_syn_slug}.iid"
            honey_syn_rules.append((honey_syn_iid_file,
                               [sym_log],
                               [f"bash build_honeypot.sh {target_iid_file} {pkg} {binary} {port} $@ > {pkg}/build_{honey_syn_slug}.log 2>&1"]))

            honey_syn_log = f"{pkg}/{honey_syn_slug}.log"
            honey_syn_cid = f"{pkg}/.{honey_syn_slug}.cid"
            honey_syn_rules.append((honey_syn_log,
                               [honey_syn_iid_file],
                               [f"-docker run --env EX_TIMEOUT={ex_timeout} --cidfile {honey_syn_cid} $$(cat {honey_syn_iid_file}) /honeypot.sh >{honey_syn_log} 2>&1",
                                f"-docker cp $$(cat {honey_syn_cid}):amps {pkg}/{honey_syn_slug}",
                                f"-docker cp $$(cat {honey_syn_cid}):real_syn_comp.out {pkg}/{honey_syn_slug}"]))
            if (pkg, binary, port) in final_eval:
                fuzz_prep_targets_final.append(fuzz_prep_rules[-1][0])
                sym_prep_targets_final.append(sym_prep_rules[-1][0])
                fuzz_targets_final.append(fuzz_rules[-1][0])
                sym_targets_final.append(sym_rules[-1][0])

variables = {'TIMEOUT': '60s'}

top_rules = []
build_rules = []

# add rules for final eval
top_rules.append(("all", ["fuzz"], []))

top_rules.append(("sym_final", sym_targets_final, []))
top_rules.append(("fuzz_final", fuzz_targets_final, []))
top_rules.append(("sym_prep_final", sym_prep_targets_final, []))
top_rules.append(("fuzz_prep_final", fuzz_prep_targets_final, []))

# add rules for individual stages
top_rules.append(("honepot_syn", [r[0] for r in honey_syn_rules], []))
top_rules.append(("sym", [r[0] for r in sym_rules], []))
top_rules.append(("fuzz", [r[0] for r in fuzz_rules], []))
top_rules.append(("sym_prep", [r[0] for r in sym_prep_rules], []))
top_rules.append(("fuzz_prep", [r[0] for r in fuzz_prep_rules], []))
top_rules.append(("instrument", [r[0] for r in target_rules], []))
top_rules.append(("build", [r[0] for r in pkg_rules], []))

# add rule for "clean"
top_rules.append((".PHONY", ["clean"], []))
top_rules.append(("clean", [], ["find . -name '*.iid' -delete"]))

build_rules.extend(pkg_rules)
build_rules.extend(target_rules)
build_rules.extend(fuzz_prep_rules)
build_rules.extend(sym_prep_rules)

def print_rules(rules):
    for rule in rules:
        rule_name, rule_deps, rule_cmds = rule
        op = '&:' if len(rule_name.split()) > 1 and rule_cmds else ':'
        print(f"{rule_name} {op} {' '.join(rule_deps)}")
        for cmd in rule_cmds:
            print(f"\t{cmd}")
        print("")


for variable, value in variables.items():
    print(f"{variable}={value}")
print("")

print_rules(top_rules)
print("\nifdef BUILD")
print_rules(build_rules)
print("endif\n")
print_rules(fuzz_rules)
print_rules(sym_rules)
print_rules(honey_syn_rules)
