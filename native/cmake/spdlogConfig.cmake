# Dependency is built from the exact pinned local source by the parent project.
if(NOT TARGET spdlog::spdlog)
  message(FATAL_ERROR "Pinned spdlog target missing")
endif()
set(spdlog_FOUND TRUE)
