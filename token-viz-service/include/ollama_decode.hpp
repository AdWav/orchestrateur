#pragma once

#include "config.hpp"

#include <nlohmann/json.hpp>
#include <string>

namespace token_viz {

struct DecodeTreeRequest {
  std::string model;
  std::string prompt;
  int top_logprobs = 5;
  int num_predict = 24;
  double temperature = -1.0;  // < 0 => omit (Ollama default)
};

// Calls Ollama /api/generate with logprobs and builds a nested tree:
// at each step, up to top_logprobs branches; only the sampled branch continues deeper.
nlohmann::json build_decode_tree(const ServiceConfig& config, const DecodeTreeRequest& request);

}  // namespace token_viz
