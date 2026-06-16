#include "embeddings.hpp"

#include "ollama_resolve.hpp"

#include <ggml.h>
#include <gguf.h>
#include <llama.h>

#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cmath>
#include <mutex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace token_viz {
namespace {

struct EmbeddingTable {
  std::string gguf_path;
  int32_t n_embd = 0;
  int64_t n_vocab = 0;
  enum ggml_type type = GGML_TYPE_F32;
  size_t token_stride = 0;
  bool embd_is_dim0 = true;
  const uint8_t* tensor_bytes = nullptr;

  int fd = -1;
  void* mmap_base = nullptr;
  size_t mmap_size = 0;

  gguf_context* gguf = nullptr;
  ggml_context* ggml = nullptr;
};

std::mutex g_emb_mutex;
std::unordered_map<std::string, EmbeddingTable> g_emb_cache;
bool g_backend_ready = false;

void ensure_backend() {
  if (!g_backend_ready) {
    llama_backend_init();
    g_backend_ready = true;
  }
}

void free_table(EmbeddingTable& table) {
  if (table.gguf != nullptr) {
    gguf_free(table.gguf);
    table.gguf = nullptr;
  }
  if (table.ggml != nullptr) {
    ggml_free(table.ggml);
    table.ggml = nullptr;
  }
  if (table.mmap_base != nullptr && table.mmap_base != MAP_FAILED) {
    munmap(table.mmap_base, table.mmap_size);
    table.mmap_base = nullptr;
  }
  if (table.fd >= 0) {
    close(table.fd);
    table.fd = -1;
  }
}

int32_t read_n_embd_from_gguf(const gguf_context* ctx) {
  static const char* keys[] = {
      "qwen2.embedding_length",
      "llama.embedding_length",
      "gemma.embedding_length",
      "general.embedding_length",
  };
  for (const char* key : keys) {
    const int64_t id = gguf_find_key(ctx, key);
    if (id >= 0) {
      const auto type = gguf_get_kv_type(ctx, id);
      if (type == GGUF_TYPE_UINT32) {
        return static_cast<int32_t>(gguf_get_val_u32(ctx, id));
      }
      if (type == GGUF_TYPE_INT32) {
        return gguf_get_val_i32(ctx, id);
      }
    }
  }
  return 0;
}

const EmbeddingTable& load_embedding_table(const std::string& cache_key, const std::string& gguf_path) {
  std::lock_guard<std::mutex> lock(g_emb_mutex);
  auto it = g_emb_cache.find(cache_key);
  if (it != g_emb_cache.end() && it->second.gguf_path == gguf_path) {
    return it->second;
  }
  if (it != g_emb_cache.end()) {
    free_table(it->second);
    g_emb_cache.erase(it);
  }

  EmbeddingTable table;
  table.gguf_path = gguf_path;

  ggml_context* ggml_ctx = nullptr;
  gguf_init_params params{};
  params.no_alloc = true;
  params.ctx = &ggml_ctx;

  table.gguf = gguf_init_from_file(gguf_path.c_str(), params);
  if (table.gguf == nullptr || ggml_ctx == nullptr) {
    throw std::runtime_error("Failed to open GGUF for embeddings: " + gguf_path);
  }
  table.ggml = ggml_ctx;

  ggml_tensor* tensor = ggml_get_tensor(ggml_ctx, "token_embd.weight");
  if (tensor == nullptr) {
    tensor = ggml_get_tensor(ggml_ctx, "tok_embd.weight");
  }
  if (tensor == nullptr) {
    throw std::runtime_error("token_embd.weight not found in GGUF");
  }

  table.n_embd = read_n_embd_from_gguf(table.gguf);
  if (table.n_embd <= 0) {
    table.n_embd = static_cast<int32_t>(tensor->ne[0]);
  }

  if (tensor->ne[0] == table.n_embd) {
    table.embd_is_dim0 = true;
    table.n_vocab = tensor->ne[1];
    table.token_stride = static_cast<size_t>(tensor->nb[1]);
  } else if (tensor->ne[1] == table.n_embd) {
    table.embd_is_dim0 = false;
    table.n_vocab = tensor->ne[0];
    table.token_stride = ggml_row_size(tensor->type, table.n_embd);
  } else {
    throw std::runtime_error("Unexpected token_embd.weight shape");
  }

  table.type = tensor->type;

  table.fd = open(gguf_path.c_str(), O_RDONLY);
  if (table.fd < 0) {
    throw std::runtime_error("Failed to open GGUF file for mmap: " + gguf_path);
  }

  struct stat st {};
  if (fstat(table.fd, &st) != 0 || st.st_size <= 0) {
    close(table.fd);
    table.fd = -1;
    throw std::runtime_error("Failed to stat GGUF file: " + gguf_path);
  }

  table.mmap_size = static_cast<size_t>(st.st_size);
  table.mmap_base = mmap(nullptr, table.mmap_size, PROT_READ, MAP_PRIVATE, table.fd, 0);
  if (table.mmap_base == MAP_FAILED) {
    close(table.fd);
    table.fd = -1;
    table.mmap_base = nullptr;
    throw std::runtime_error("Failed to mmap GGUF file: " + gguf_path);
  }

  const int64_t tensor_id = gguf_find_tensor(table.gguf, tensor->name);
  if (tensor_id < 0) {
    throw std::runtime_error("token_embd tensor id not found in GGUF metadata");
  }

  const size_t data_base = gguf_get_data_offset(table.gguf);
  const size_t tensor_off = gguf_get_tensor_offset(table.gguf, tensor_id);
  table.tensor_bytes =
      static_cast<const uint8_t*>(table.mmap_base) + data_base + tensor_off;

  auto [inserted_it, _] = g_emb_cache.emplace(cache_key, std::move(table));
  return inserted_it->second;
}

std::vector<float> dequantize_token_row(const EmbeddingTable& table, int token_id) {
  if (token_id < 0 || token_id >= table.n_vocab) {
    throw std::invalid_argument("token id out of vocabulary range");
  }

  const size_t offset = static_cast<size_t>(token_id) * table.token_stride;
  const void* row_ptr = table.tensor_bytes + offset;

  std::vector<float> values(static_cast<size_t>(table.n_embd));
  const ggml_type_traits* traits = ggml_get_type_traits(table.type);
  if (traits == nullptr || traits->to_float == nullptr) {
    throw std::runtime_error("Unsupported embedding quantization type");
  }
  traits->to_float(row_ptr, values.data(), table.n_embd);
  return values;
}

nlohmann::json vector_stats(const std::vector<float>& values) {
  if (values.empty()) {
    return {{"min", 0.0}, {"max", 0.0}, {"mean", 0.0}, {"std", 0.0}};
  }
  double sum = 0.0;
  double sum_sq = 0.0;
  float min_v = values.front();
  float max_v = values.front();
  for (float v : values) {
    min_v = std::min(min_v, v);
    max_v = std::max(max_v, v);
    sum += v;
    sum_sq += static_cast<double>(v) * static_cast<double>(v);
  }
  const double mean = sum / static_cast<double>(values.size());
  const double variance = sum_sq / static_cast<double>(values.size()) - mean * mean;
  return {
      {"min", min_v},
      {"max", max_v},
      {"mean", mean},
      {"std", std::sqrt(std::max(0.0, variance))},
  };
}

}  // namespace

nlohmann::json extract_embeddings(
    const ServiceConfig& config,
    ModelTokenizer& tokenizer,
    const EmbeddingsRequest& request) {
  if (request.model.empty()) {
    throw std::invalid_argument("model is required");
  }
  if (request.text.empty()) {
    throw std::invalid_argument("text is required");
  }

  ensure_backend();

  const TokenizeResult tokenized = tokenizer.tokenize(request.model, request.text);
  const std::string gguf_path =
      resolve_gguf_path(config.ollama_base_url, config.ollama_models_dir, request.model);
  const EmbeddingTable& table = load_embedding_table(request.model, gguf_path);

  nlohmann::json tokens = nlohmann::json::array();
  for (std::size_t i = 0; i < tokenized.tokens.size(); ++i) {
    if (request.token_index >= 0 && static_cast<int>(i) != request.token_index) {
      continue;
    }

    const auto& piece = tokenized.tokens[i];
    const std::vector<float> vector = dequantize_token_row(table, piece.id);

    tokens.push_back({
        {"index", i},
        {"id", piece.id},
        {"text", piece.text},
        {"vector", vector},
        {"stats", vector_stats(vector)},
    });
  }

  if (tokens.empty()) {
    throw std::invalid_argument("token_index out of range");
  }

  return {
      {"model", request.model},
      {"gguf_path", gguf_path},
      {"source", "gguf_token_embd"},
      {"tensor", "token_embd.weight"},
      {"n_embd", table.n_embd},
      {"n_vocab", table.n_vocab},
      {"quantization", static_cast<int>(table.type)},
      {"token_count", tokenized.tokens.size()},
      {"positional_note",
       "Vecteurs token_embd bruts. Les modèles RoPE (Qwen, Llama…) appliquent la position "
       "pendant le forward pass, pas par addition sur cette table."},
      {"tokens", tokens},
  };
}

}  // namespace token_viz
