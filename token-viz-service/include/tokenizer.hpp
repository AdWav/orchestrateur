#pragma once

#include "config.hpp"

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace token_viz {

struct TokenPiece {
  int id = -1;
  std::string text;
};

struct TokenizeResult {
  std::string model;
  std::string source = "llama_cpp";
  std::string gguf_path;
  std::vector<TokenPiece> tokens;
};

class ModelTokenizer {
 public:
  explicit ModelTokenizer(ServiceConfig config);

  TokenizeResult tokenize(const std::string& model, const std::string& text);
  nlohmann::json capabilities() const;

 private:
  ServiceConfig config_;
};

}  // namespace token_viz
