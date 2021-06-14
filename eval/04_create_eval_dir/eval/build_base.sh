#!/bin/bash
set -eux

PKG=$1
VERSION=$2
BASE_IID_FILE=$(realpath "$3")

BASE_CID_FILE=${BASE_IID_FILE%%.iid}.cid
VERSION_FILE="${PKG}/version"

docker volume create ampfuzz_build_cache

# perform arcane magic:
# docker does not allow mounting volumes during build,
# therefore we emulate the build by running in a fresh container
# and then committing this container to a new image.
# Since we override the cmd and entrypoint during run,
# we need to "revert" these changes during commit

docker run -v ampfuzz_build_cache:/var/ampfuzz --cidfile "${BASE_CID_FILE}" --label "pkg=${PKG}" ampfuzz python 01_prep_package.py -v "${VERSION}" "${PKG}"
docker commit -c 'CMD ["/bin/bash"]' $(cat ${BASE_CID_FILE}) > ${BASE_IID_FILE}