#!/usr/bin/env python3
import glob
import os
import os.path
import argparse
import subprocess
import shutil
import sys
from os import walk
from time import sleep

# get the of location of script
ampfuzz_bin = os.path.dirname(os.path.realpath(__file__))

ampfuzz_var = '/var/ampfuzz'

# get the environment ready
my_env = os.environ.copy()
my_env['DEBIAN_FRONTEND'] = 'noninteractive'
my_env['CC'] = '/usr/bin/clang-11'
my_env['CXX'] = 'usr/bin/clang++-11'
my_env['PATH'] = '/usr/lib/llvm-11/bin:/usr/bin/zsh:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'


def dparser():
    par = argparse.ArgumentParser(
        description='sym_target expects a debian package name binary name together with path using debian as root, examples are in ranked_packages.json')
    par.add_argument('binary', type=str,
                     help='Binary name and path')
    par.add_argument('port', type=int, default=53,
                     help='Port in use')
    par.add_argument('-i', '--inetd', action='store_true', help='Wrap with inetd harness')
    par.add_argument('args', type=str, nargs='*')
    return par


def exec_command(name, options, input=None, asuser=None):
    command = []
    if asuser is not None:
        command.append('sudo')
        command.append('-E')
        command.append('-u')
        command.append(asuser)
        command.append('--')
    command.append(name)
    command.extend(options)
    if input is not None:
        command.append(input)

    print(command)

    subprocess.check_call(command,
                          stdin=sys.stdin.fileno(),
                          stdout=sys.stdout.fileno(),
                          stderr=sys.stderr.fileno(),
                          env=my_env)


def par_exec_command(name, options, input=None, asuser=None, stdin=None, stdout=None, stderr=None):
    command = []
    if asuser is not None:
        command.append('sudo')
        command.append('-E')
        command.append('-u')
        command.append(asuser)
        command.append('--')
    command.append(name)
    command.extend(options)
    if input is not None:
        command.append(input)

    print(command)
    stdin = stdin or sys.stdin.fileno()
    stdout = stdout or sys.stdout.fileno()
    stderr = stderr or sys.stderr.fileno()

    p = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr, env=my_env)
    return p


def sym(executable, ports, args, inetd=False):
    out = executable + '.sym.result'
    timeout_start = 2
    if 'EX_TIMEOUT' in os.environ:
        timeout_reply = int(os.environ['EX_TIMEOUT'])
    else:
        timeout_reply = 10
    port = str(ports[0])
    # finally - symbolically executing
    sym_ex = f"{executable}.sym"
    # wrap with inetd?
    if inetd:
        exec_command(ampfuzz_bin + '/harnesses/inetd/wrap_only_bin.sh', [port, sym_ex])
        sym_ex = f"{sym_ex}.wrap.{port}"

    amps_dir = '/amps'

    for amp in glob.glob(f'{amps_dir}/amp_*'):
        factor = float(amp.split('_')[-2])
        if factor < 1.0:
            continue
        with open(out, 'ab') as sym_out, open(os.path.join(amps_dir, amp), 'rb') as amp_in, open(
                os.path.join(amps_dir, amp + '.out'), 'wb') as amp_out:
            p = par_exec_command(sym_ex, args, stderr=sym_out)
            sleep(timeout_start)  # allow some start-up time
            par_exec_command('nc', ['-u', '127.0.0.1', port], stdin=amp_in, stdout=amp_out)
            sleep(timeout_reply)  # allow some computation time
            p.terminate()


def main():
    # from IPython import embed; embed()
    # get the arg
    parser = dparser()
    args = parser.parse_args()
    executable = args.binary
    fuzzee_args = args.args

    ports = [args.port]

    # sym?
    sym(executable, ports, fuzzee_args, inetd=args.inetd)


if __name__ == '__main__':
    main()
