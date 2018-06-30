#!/bin/bash
LLVM_DIR=bin/llvm

build_llvm() {
  mkdir -p "$LLVM_DIR"
  LLVM_SRC_DIR="$PWD/llvm"
  pushd "$LLVM_DIR"
  export CC=gcc-4.8
  export CXX=g++-4.8
  cmake "$LLVM_SRC_DIR" \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_INCLUDE_DOCS=0 \
    -DLLVM_INCLUDE_TESTS=0 \
    -DLLVM_INCLUDE_EXAMPLES=0 \
    -DLLVM_INCLUDE_UTILS=0 \
    -DLLVM_BINDINGS_LIST="" \
    -DWITH_POLLY=0
  make -j$(nproc)
  popd
}

build_llvm
