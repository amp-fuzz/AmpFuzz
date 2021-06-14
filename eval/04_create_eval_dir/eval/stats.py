#!/usr/bin/env python3
import csv
import os
import json

with open('./package_matches.json') as f:
    packages = json.load(f)

all_packages = set(packages.keys())

all_binaries = [(pkg, binary) for pkg, pkg_info in packages.items() for binary in pkg_info['binaries']]

all_fuzz_targets = [(pkg, binary, port) for pkg, pkg_info in packages.items() for binary, ports in
                    pkg_info['binaries'].items() for port in ports]

compiled_packages = set()
for pkg in packages:
    if os.path.exists(os.path.join(pkg, '.base.iid')):
        compiled_packages.add(pkg)

instrumented_binaries = set()
compiled_binaries = set()
for pkg, pkg_info in packages.items():
    if pkg in compiled_packages:
        for binary in pkg_info['binaries']:
            compiled_binaries.add((pkg, binary))
            if os.path.exists(os.path.join(pkg, f".{binary.replace('/', '_')}.iid")):
                instrumented_binaries.add((pkg, binary))

compiled_fuzz_targets = set()
instrumented_fuzz_targets = set()
branch_fuzz_targets = set()
ready_fuzz_targets = set()
best_amp_targets = dict()

for pkg, binary, port in all_fuzz_targets:
    if pkg in compiled_packages:
        compiled_fuzz_targets.add((pkg, binary, port))

        if (pkg, binary) in instrumented_binaries:
            instrumented_fuzz_targets.add((pkg, binary, port))

            fuzz_log_path = os.path.join(pkg, f"fuzz_{binary.replace('/', '_')}_{port}.log")
            if os.path.exists(fuzz_log_path):
                with open(fuzz_log_path) as f:
                    fuzz_log = f.read()
                if '-- OVERVIEW --' in fuzz_log:
                    branch_fuzz_targets.add((pkg, binary, port))
                    last_round = fuzz_log.rsplit('ROUND:', maxsplit=1)[1]
                    max_round = int(last_round.split(',', maxsplit=1)[0])
                    best_amp = float(last_round.split('best:', maxsplit=1)[1].split('x')[0])
                    if max_round > 1 or '[\'/ampfuzz/build/fuzzer\'' not in fuzz_log:
                        ready_fuzz_targets.add((pkg, binary, port))
                        if best_amp>0:
                            best_amp_targets[(pkg, binary, port)] = best_amp



def to_safe_str(s):
    return s.replace('/', '').replace(' ', '_')


def gen_stats(name, labels, data):
    assert len(labels) + 1 == len(data)
    print(f'-- {name.upper():^8} --             |   rel   |   abs')
    n_global = len(data[0])
    for label, (old, new) in zip(labels, zip(data, data[1:])):
        n_old = len(old)
        n_new = len(new)
        pct = f"{n_new / n_old:.2%}" if n_old > 0 else "-- %"
        pct_global = f"{n_new / n_global:.2%}" if n_global > 0 else "-- %"
        print(f"  {label:<13}: {n_new:4}/{n_old:4} | {pct:>7} | {pct_global:>7}")

        safe_name = to_safe_str(name)
        safe_label = to_safe_str(label)

        with open(f'./{safe_name}_success_{safe_label}.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerows(sorted(new))

        failed = set(old) - set(new)
        with open(f'./{safe_name}_failed_{safe_label}.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerows(sorted(failed))
    print()


gen_stats('packages', ['compiled', 'instrumented', 'w/ feedback', 'fuzz-ready'],
          [{(p,) for p in all_packages}, {(p,) for p in compiled_packages},
           {(p,) for p, _, _ in instrumented_fuzz_targets}, {(p,) for p, b, po in branch_fuzz_targets},
           {(p,) for p, _, _ in ready_fuzz_targets}])
gen_stats('binaries', ['compiled', 'instrumented', 'w/ feedback', 'fuzz-ready'],
          [all_binaries, compiled_binaries, instrumented_binaries, {(p, b) for p, b, _ in branch_fuzz_targets},
           {(p, b) for p, b, _ in ready_fuzz_targets}])
gen_stats('targets', ['compiled', 'instrumented', 'w/ feedback', 'fuzz-ready'],
          [all_fuzz_targets, compiled_fuzz_targets, instrumented_fuzz_targets, branch_fuzz_targets, ready_fuzz_targets])

print(f'-- TOP AMPS --')
for amp, pkg, binary, port in sorted(((amp, pkg, binary, port) for (pkg, binary, port), amp in best_amp_targets.items()), reverse=True):
    print(f'[{pkg}] {binary} {port} {amp:.2f}x')
