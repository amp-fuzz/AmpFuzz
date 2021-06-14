#!/bin/bash
set -eux

TARGET_IID_FILE=$(realpath "$1")
PKG=$2
TARGET=$3
TARGETNAME=${TARGET//\//_}
PORT=$4
SYM_IID_FILE=$(realpath "$5")
ARGS_FILE="args"
CONFIG_SCRIPT="config.sh"
FUZZ_ARGS_FILE="fuzz_args"
SYM_SCRIPT="sym.sh"

TARGET_IID=$(cat "${TARGET_IID_FILE}")

symdir="${PKG}/${TARGETNAME}/${PORT}"
mkdir -p ${symdir}

cp -r "${PKG}/fuzz_${TARGETNAME}_${PORT}/amps" ${symdir}

pushd ${symdir}

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

cat > ${SYM_SCRIPT} <<EOF
#!/bin/bash
python /ampfuzz/build/04_sym_target.py ${fuzz_args} "${TARGET}" "${PORT}" -- ${args}
EOF

cat > Dockerfile <<EOF
FROM ${TARGET_IID}
COPY ${CONFIG_SCRIPT} ${SYM_SCRIPT} /
RUN chmod +x /${CONFIG_SCRIPT} /${SYM_SCRIPT}
RUN /${CONFIG_SCRIPT}
RUN /symcc_build_simple/make_sym ${TARGET}

COPY amps /amps

ENV CC=clang-11
ENV CXX=clang++-11

ENV PATH=/symcc_build_simple:\$PATH
ENV SYMCC_LIBCXX_PATH=/libcxx_symcc_install

WORKDIR /
EOF

docker build --no-cache --iidfile "${SYM_IID_FILE}" .

popd
