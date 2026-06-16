cmake_minimum_required(VERSION 3.16)
project(token-viz-service CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT DEFINED LLAMA_CPP_DIR)
  message(FATAL_ERROR "Pass -DLLAMA_CPP_DIR=/path/to/llama.cpp")
endif()

find_package(CURL REQUIRED)
find_package(Threads REQUIRED)

set(LLAMA_BUILD_COMMON OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

add_subdirectory(${LLAMA_CPP_DIR} llama_cpp_build EXCLUDE_FROM_ALL)

add_executable(token-viz-service
  src/main.cpp
  src/tokenizer.cpp
  src/ollama_resolve.cpp
  src/ollama_decode.cpp
  src/model_inspect.cpp
  src/embeddings.cpp
  src/config.cpp
)

target_include_directories(token-viz-service PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/third_party
)

target_link_libraries(token-viz-service PRIVATE
  llama
  CURL::libcurl
  Threads::Threads
)

if(UNIX AND NOT APPLE)
  target_link_libraries(token-viz-service PRIVATE dl m)
endif()
