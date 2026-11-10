cmake_minimum_required(VERSION 3.16)
project(artic_core CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
add_library(artic_core SHARED core/artic_core.cpp)
set_target_properties(artic_core PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/core/build
  ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/core/build
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/core/build)
