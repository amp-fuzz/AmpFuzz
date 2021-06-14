FROM ubuntu:20.10

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

# get LLVM-11
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y \
        llvm-11-dev \
        clang-11 \
        libblocksruntime-dev

# get other tools
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y \
        cmake \
        cargo \
        zlib1g-dev \
        python-is-python3 \
        ninja-build \
        zsh \
        libtirpc-dev \
        libsystemd-dev \
        git \
        devscripts \
        python3-pip \
        vim \
        tcpdump \
        net-tools \
        netcat \
        ncat \
        libz3-dev \
        apt-utils && \
    apt-get clean

COPY . /ampfuzz

ENV Z3_DIR=/usr/bin

### prepare symbolic execution
RUN ln -s /ampfuzz/symcc_amp /symcc_source
RUN ln -s /ampfuzz/llvm_mode/libcxx/llvm /llvm_source

WORKDIR /symcc_build_simple
RUN cmake -G Ninja \
        -DQSYM_BACKEND=OFF \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DZ3_TRUST_SYSTEM_VERSION=on \
        /symcc_source \
    && ninja check

# Build libc++ with SymCC using the simple backend
WORKDIR /libcxx_symcc
RUN export SYMCC_REGULAR_LIBCXX=yes SYMCC_NO_SYMBOLIC_INPUT=yes \
    && mkdir /libcxx_symcc_build \
    && cd /libcxx_symcc_build \
    && cmake -G Ninja /llvm_source/llvm \
         -DLLVM_ENABLE_PROJECTS="libcxx;libcxxabi" \
         -DLLVM_TARGETS_TO_BUILD="X86" \
         -DLLVM_DISTRIBUTION_COMPONENTS="cxx;cxxabi;cxx-headers" \
         -DLLVM_INCLUDE_TESTS=OFF \
         -DLLVM_INCLUDE_EXAMPLES=OFF \
         -DLLVM_INCLUDE_BENCHMARKS=OFF \
         -DLLVM_INCLUDE_TOOLS=OFF \
         -DLLVM_BUILD_TOOLS=OFF \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_INSTALL_PREFIX=/libcxx_symcc_install \
         -DCMAKE_C_COMPILER=/symcc_build_simple/symcc \
         -DCMAKE_CXX_COMPILER=/symcc_build_simple/sym++ \
    && ninja distribution \
    && ninja install-distribution

### done prepare symbolic execution

# add source repositories, prefer local repositories
RUN cp /etc/apt/sources.list /etc/apt/sources.list~ && \
    sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list && \
    mv /etc/apt/sources.list /etc/apt/sources.list.d/99_default.list && \
    echo "" > /etc/apt/sources.list && \
    echo 'Package: *\nPin: origin ""\nPin-Priority: 9999' > /etc/apt/preferences.d/prefer_local && \
    apt-get update

# create non-root user
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y sudo && useradd user && echo "user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-user
# prevent env_reset and secure_path
RUN sed -Ei 's/^(Defaults\s+)env_reset$/\1!env_reset/g' /etc/sudoers && \
    sed -Ei 's/^(Defaults\s+)secure_path.*$/\1!secure_path/g' /etc/sudoers

RUN DEBIAN_FRONTEND=noninteractive \
    apt-get -y install debconf-utils && \
    echo resolvconf resolvconf/linkify-resolvconf boolean false | debconf-set-selections && \
    apt-get -y install resolvconf

# add zsh to path
ENV PATH="/usr/bin/zsh:${PATH}"

# add llvm to path,
# but do not take precedence
ENV PATH="$PATH:/usr/lib/llvm-11/bin"

# install extra tools
RUN pip3 install wllvm

# build
RUN rm -rf /ampfuzz/build && \
    mkdir -p /ampfuzz/build
WORKDIR /ampfuzz/build
RUN cmake .. && make -j $(nproc) && make -j $(nproc) install

ENV LLVM_COMPILER_PATH=/usr/lib/llvm-11/bin
ENV CC=/ampfuzz/build/pre_clang
ENV CXX=/ampfuzz/build/pre_clang++
