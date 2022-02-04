#!/usr/bin/env python3
# coding: utf-8
from functools import reduce
from operator import __and__

import pandas as pd
import numpy as np

CONF_KEYS = ['startup_time_limit', 'response_time_limit', 'disable_listen_ready', 'early_termination',
             'disable_amp_mutation', 'timeout']


def print_latex_table(input_file):
    # Load
    raw_df = pd.read_json(input_file)

    # Filter for correct configuration
    configs = [k for k, _ in raw_df.groupby(CONF_KEYS)]

    for config in configs:
        df = raw_df[reduce(__and__, (raw_df[k] == v for k, v in zip(CONF_KEYS, configs[0])))].copy()

        # Merge/Rename
        df["program"] = "(" + df["package"] + ") " + df["program"].str.rsplit("/", n=1).str.get(1)
        # Cleanup
        df = df.drop(
            columns=set(df.columns) - {"program", "port", "n_paths", "n_msg_types", "n_amp_types", "max_amp_l2",
                                       "max_amp_l7"})
        # Aggregate
        result = df.groupby(["program", "port"]).agg([np.max, np.mean, np.std])
        # Niceify
        for col in result.columns.levels[0]:
            if col in {"max_amp_l2", "max_amp_l7"}:
                max_round = 2
                avg_round = 2
            else:
                max_round = 0
                avg_round = 1

            result[(col, "max")] = result[(col, "amax")].round(max_round)
            if max_round == 0:
                result[(col, "max")] = result[(col, "max")].astype(int)

            result[(col, "avg")] = (
                    "{\\scriptsize $\\begin{aligned}"
                    + result[(col, "mean")].round(avg_round).astype(str).str.replace('.', '&.', regex=False)
                    + "\\\\[-5pt]\\pm "
                    + result[(col, "std")].round(avg_round).astype(str).str.replace('.', '&.', regex=False)
                    + "\\end{aligned}$}"
            )
        result.drop(columns=[(col, agg) for agg in ["amax", "mean", "std"] for col in result.columns.levels[0]],
                    inplace=True)
        result.rename(columns={"n_paths": "\\# paths", "n_msg_types": "\\# requests", "n_amp_types": "\\# amps",
                               "max_amp_l2": "$\\max(BAF_{L2})$", "max_amp_l7": "$\\max(BAF_{L7})$",
                               "max": "{\\footnotesize best}",
                               "avg": r"{\scriptsize $\begin{aligned}\text{mean}& \\[-5pt]\pm \text{std}&\end{aligned}$}"},
                      inplace=True)
        # Gen latex
        with pd.option_context("max_colwidth", 1000):
            latex_code = result.to_latex(na_rep='', multicolumn=True, escape=False)
        # Cleanup code
        latex_code = latex_code.replace(' 0 ', ' - ').replace(
            '{\\scriptsize $\\begin{aligned}0&.0\\\\[-5pt]\\pm 0&.0\\end{aligned}$}', '').replace('$nan \pm nan$',
                                                                                                  '').replace(
            'inf', '$\\infty$')

        # Print
        print("\n"*3)
        print("="*128)
        print(f"Results for config {dict(zip(CONF_KEYS, config))}")
        print("="*128)
        print(latex_code)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', nargs='?', default='results/results.json',
                        help='path to results.json (generated by 01_compute_amp_stats.py)')
    args = parser.parse_args()

    print_latex_table(args.input_file)


if __name__ == '__main__':
    main()