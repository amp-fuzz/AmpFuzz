#!/bin/bash
set -eux

TARGET_IID_FILE=$(realpath "$1")
PKG=$2
TARGET=$3
TARGETNAME=${TARGET//\//_}
PORT=$4
FUZZ_IID_FILE=$(realpath "$5")
ARGS_FILE="args"
CONFIG_SCRIPT="config.sh"
FUZZ_ARGS_FILE="fuzz_args"
FUZZ_SCRIPT="fuzz.sh"

TARGET_IID=$(cat "${TARGET_IID_FILE}")

fuzzdir="${PKG}/${TARGETNAME}/${PORT}"
mkdir -p ${fuzzdir}
pushd ${fuzzdir}

if [ ! -f "${CONFIG_SCRIPT}" ]; then
  cat >"${CONFIG_SCRIPT}" <<EOF
#!/bin/sh
# AmpFuzz pre-fuzz config script
# Use this script to create/modify
# config files for the fuzz target
EOF
fi

args=""
if [ -f "${ARGS_FILE}" ]; then
  args=$(cat ${ARGS_FILE}|tr '[:space:]' ' ')
fi

fuzz_args=""
if [ -f "${FUZZ_ARGS_FILE}" ]; then
  fuzz_args=$(cat ${FUZZ_ARGS_FILE}|tr '[:space:]' ' ')
fi

cat > ${FUZZ_SCRIPT} <<EOF
#!/bin/bash
python /ampfuzz/build/03_fuzz_target.py ${fuzz_args} "${TARGET}" "${PORT}" -- ${args}
EOF

cat > Dockerfile <<EOF
FROM ${TARGET_IID}
COPY ${CONFIG_SCRIPT} ${FUZZ_SCRIPT} /
RUN chmod +x /${CONFIG_SCRIPT} /${FUZZ_SCRIPT}
RUN /${CONFIG_SCRIPT}
WORKDIR /
LABEL "port"="${PORT}"
EOF

docker build --cpu-quota=100000 --no-cache --iidfile "${FUZZ_IID_FILE}" .

popd