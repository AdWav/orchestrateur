#pragma once

#include <string>
#include <vector>

namespace token_viz {

struct ServiceConfig {
  std::string bind_host = "127.0.0.1";
  int port = 8091;
  std::string ollama_base_url = "http://127.0.0.1:11434";
  std::string ollama_models_dir;
  std::vector<std::string> cors_origins;
  std::string static_dir = "static";
};

ServiceConfig load_config_from_env();

}  // namespace token_viz
