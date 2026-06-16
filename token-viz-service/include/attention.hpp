#pragma once

#include "config.hpp"

#include <nlohmann/json.hpp>
#include <string>

namespace token_viz {

struct AttentionRequest {
  std::string model;
  std::string text;
  int layer = 0;
  int head = 0;
  int max_tokens = 64;
};

nlohmann::json extract_attention_map(
    const ServiceConfig& config,
    const AttentionRequest& request);

}  // namespace token_viz
