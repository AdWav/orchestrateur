#include "tokenizer.hpp"

#include "ollama_resolve.hpp"

#include <llama.h>

#include <mutex>
#include <stdexcept>
#include <unordered_map>

namespace token_viz {
namespace {

struct CachedVocab {
  std::string gguf_path;
  llama_model* model = nullptr;
};

std::mutex g_cache_mutex;
std::unordered_map<std::string, CachedVocab> g_vocab_cache;
bool g_backend_ready = false;

void ensure_backend() {
  if (!g_backend_ready) {
    llama_backend_init();
    g_backend_ready = true;
  }
}

llama_model* load_vocab_model(const std::string& cache_key, const std::string& gguf_path) {
  std::lock_guard<std::mutex> lock(g_cache_mutex);
  auto it = g_vocab_cache.find(cache_key);
  if (it != g_vocab_cache.end() && it->second.gguf_path == gguf_path && it->second.model != nullptr) {
    return it->second.model;
  }

  if (it != g_vocab_cache.end() && it->second.model != nullptr) {
    llama_model_free(it->second.model);
    g_vocab_cache.erase(it);
  }

  llama_model_params params = llama_model_default_params();
  params.vocab_only = true;
  params.use_mmap = true;
  params.use_mlock = false;

  llama_model* model = llama_model_load_from_file(gguf_path.c_str(), params);
  if (model == nullptr) {
    throw std::runtime_error("Failed to load GGUF vocabulary: " + gguf_path);
  }

  g_vocab_cache[cache_key] = CachedVocab{gguf_path, model};
  return model;
}

std::vector<TokenPiece> tokenize_text(llama_model* model, const std::string& text) {
  const llama_vocab* vocab = llama_model_get_vocab(model);
  if (vocab == nullptr) {
    throw std::runtime_error("Model vocabulary unavailable");
  }

  const int32_t max_tokens = static_cast<int32_t>(text.size()) + 16;
  std::vector<llama_token> token_ids(static_cast<size_t>(max_tokens));

  const int32_t count = llama_tokenize(
      vocab,
      text.c_str(),
      static_cast<int32_t>(text.size()),
      token_ids.data(),
      max_tokens,
      /*add_special*/ false,
      /*parse_special*/ false);

  if (count < 0) {
    throw std::runtime_error("llama_tokenize failed");
  }

  token_ids.resize(static_cast<size_t>(count));
  std::vector<TokenPiece> pieces;
  pieces.reserve(token_ids.size());

  char buffer[512];
  for (llama_token token_id : token_ids) {
    const int32_t length = llama_token_to_piece(
        vocab, token_id, buffer, static_cast<int32_t>(sizeof(buffer)), 0, false);
    if (length < 0) {
      pieces.push_back(TokenPiece{static_cast<int>(token_id), ""});
      continue;
    }
    pieces.push_back(TokenPiece{static_cast<int>(token_id), std::string(buffer, length)});
  }

  return pieces;
}

nlohmann::json pieces_to_json(const std::vector<TokenPiece>& pieces) {
  nlohmann::json tokens = nlohmann::json::array();
  for (const auto& piece : pieces) {
    tokens.push_back({{"id", piece.id}, {"text", piece.text}});
  }
  return tokens;
}

}  // namespace

ModelTokenizer::ModelTokenizer(ServiceConfig config) : config_(std::move(config)) {
  ensure_backend();
}

TokenizeResult ModelTokenizer::tokenize(const std::string& model, const std::string& text) {
  if (text.empty()) {
    throw std::invalid_argument("text must not be empty");
  }

  const std::string gguf_path =
      resolve_gguf_path(config_.ollama_base_url, config_.ollama_models_dir, model);
  llama_model* vocab_model = load_vocab_model(model, gguf_path);

  TokenizeResult result;
  result.model = model;
  result.gguf_path = gguf_path;
  result.tokens = tokenize_text(vocab_model, text);
  return result;
}

nlohmann::json ModelTokenizer::capabilities() const {
  return {
      {"source", "llama_cpp"},
      {"ollama_api", false},
      {"llama_cpp", true},
      {"service", "token-viz-service"},
      {"ollama_base_url", config_.ollama_base_url},
      {"ollama_models_dir", config_.ollama_models_dir},
  };
}

}  // namespace token_viz
