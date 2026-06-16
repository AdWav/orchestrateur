#pragma once

#include "config.hpp"
#include "tokenizer.hpp"

#include <nlohmann/json.hpp>
#include <string>

namespace token_viz {

struct EmbeddingsRequest {
  std::string model;
  std::string text;
  int token_index = -1;  // < 0 => all tokens
};

nlohmann::json extract_embeddings(
    const ServiceConfig& config,
    ModelTokenizer& tokenizer,
    const EmbeddingsRequest& request);

}  // namespace token_viz
