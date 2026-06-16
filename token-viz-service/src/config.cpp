#include "config.hpp"

#include <cstdlib>
#include <sstream>
#include <stdexcept>

namespace token_viz {

namespace {

std::string env_or(const char* key, const std::string& fallback) {
  const char* value = std::getenv(key);
  return value != nullptr && value[0] != '\0' ? std::string(value) : fallback;
}

std::vector<std::string> split_csv(const std::string& raw) {
  std::vector<std::string> parts;
  std::stringstream stream(raw);
  std::string item;
  while (std::getline(stream, item, ',')) {
    if (!item.empty()) {
      parts.push_back(item);
    }
  }
  return parts;
}

}  // namespace

ServiceConfig load_config_from_env() {
  ServiceConfig config;
  config.bind_host = env_or("TOKEN_VIZ_BIND_HOST", config.bind_host);
  config.port = std::stoi(env_or("TOKEN_VIZ_PORT", std::to_string(config.port)));
  config.ollama_base_url = env_or("OLLAMA_BASE_URL", config.ollama_base_url);
  config.ollama_models_dir = env_or("OLLAMA_MODELS_DIR", config.ollama_models_dir);
  config.static_dir = env_or("TOKEN_VIZ_STATIC_DIR", config.static_dir);

  const std::string cors = env_or(
      "TOKEN_VIZ_CORS_ORIGINS",
      "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173");
  config.cors_origins = split_csv(cors);

  if (config.ollama_models_dir.empty()) {
    throw std::runtime_error(
        "OLLAMA_MODELS_DIR is required (Ollama data root with models/blobs/).");
  }

  return config;
}

}  // namespace token_viz
