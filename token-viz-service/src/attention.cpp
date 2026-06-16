#include "attention.hpp"

#include "ollama_resolve.hpp"

#include <ggml-backend.h>
#include <ggml.h>
#include <llama.h>

#include <algorithm>
#include <cmath>
#include <mutex>
#include <regex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace token_viz {
namespace {

struct ModelHolder {
  std::string gguf_path;
  llama_model* model = nullptr;
};

std::mutex g_model_mutex;
std::unordered_map<std::string, ModelHolder> g_model_cache;
bool g_backend_ready = false;

void ensure_backend() {
  if (!g_backend_ready) {
    llama_backend_init();
    g_backend_ready = true;
  }
}

llama_model* load_model(const std::string& key, const std::string& gguf_path) {
  std::lock_guard<std::mutex> lock(g_model_mutex);
  auto it = g_model_cache.find(key);
  if (it != g_model_cache.end() && it->second.gguf_path == gguf_path && it->second.model != nullptr) {
    return it->second.model;
  }
  if (it != g_model_cache.end() && it->second.model != nullptr) {
    llama_model_free(it->second.model);
    g_model_cache.erase(it);
  }

  llama_model_params model_params = llama_model_default_params();
  model_params.vocab_only = false;
  model_params.use_mmap = true;
  model_params.use_mlock = false;
  model_params.n_gpu_layers = 0;

  llama_model* model = llama_model_load_from_file(gguf_path.c_str(), model_params);
  if (model == nullptr) {
    throw std::runtime_error("Failed to load model for attention extraction: " + gguf_path);
  }

  g_model_cache[key] = ModelHolder{gguf_path, model};
  return model;
}

std::vector<llama_token> tokenize(const llama_vocab* vocab, const std::string& text, int max_tokens) {
  if (text.empty()) {
    throw std::invalid_argument("text is required");
  }
  const int32_t needed =
      -llama_tokenize(vocab, text.c_str(), static_cast<int32_t>(text.size()), nullptr, 0, true, true);
  if (needed <= 0) {
    throw std::runtime_error("llama_tokenize failed to size tokens");
  }

  std::vector<llama_token> tokens(static_cast<size_t>(needed));
  const int32_t n = llama_tokenize(
      vocab,
      text.c_str(),
      static_cast<int32_t>(text.size()),
      tokens.data(),
      needed,
      true,
      true);
  if (n <= 0) {
    throw std::runtime_error("llama_tokenize failed");
  }
  tokens.resize(static_cast<size_t>(n));
  if (max_tokens > 0 && static_cast<int>(tokens.size()) > max_tokens) {
    tokens.resize(static_cast<size_t>(max_tokens));
  }
  return tokens;
}

std::vector<std::string> token_texts(const llama_vocab* vocab, const std::vector<llama_token>& ids) {
  std::vector<std::string> out;
  out.reserve(ids.size());
  char buf[512];
  for (llama_token id : ids) {
    const int32_t n = llama_token_to_piece(vocab, id, buf, sizeof(buf), 0, false);
    if (n < 0) {
      out.emplace_back("");
    } else {
      out.emplace_back(buf, buf + n);
    }
  }
  return out;
}

struct CaptureState {
  int requested_layer = 0;
  int requested_head = 0;
  int n_tokens = 0;

  bool captured = false;
  bool used_transpose = false;
  std::string tensor_name;
  std::vector<int64_t> shape = {0, 0, 0, 0};
  std::vector<std::vector<double>> matrix;
  std::vector<std::string> observed;
};

bool name_matches_layer(const std::string& name, int layer) {
  const std::string needle = "blk." + std::to_string(layer) + ".";
  if (name.find(needle) != std::string::npos) {
    return true;
  }
  const std::regex alt_re("attn[-_]" + std::to_string(layer) + R"(\b)");
  return std::regex_search(name, alt_re);
}

bool eval_callback(struct ggml_tensor* t, bool ask, void* user_data) {
  auto* st = static_cast<CaptureState*>(user_data);
  const std::string name = ggml_get_name(t) != nullptr ? ggml_get_name(t) : "";
  const std::string op = ggml_op_desc(t) != nullptr ? ggml_op_desc(t) : "";

  if (ask) {
    return true;
  }

  if (st->captured) {
    return true;
  }

  const int64_t ne0 = t->ne[0];
  const int64_t ne1 = t->ne[1];
  const int64_t ne2 = t->ne[2];
  const int64_t ne3 = t->ne[3];
  if (st->observed.size() < 64) {
    st->observed.push_back(
        (name.empty() ? "<unnamed>" : name) + " | " + (op.empty() ? "<op?>" : op) + " | " +
        std::to_string(ne0) + "x" + std::to_string(ne1) + "x" + std::to_string(ne2) + "x" +
        std::to_string(ne3));
  }
  const bool maybe_attn =
      op.find("SOFT_MAX") != std::string::npos ||
      (!name.empty() && name.find("kq") != std::string::npos) ||
      (!name.empty() && name.find("attn") != std::string::npos);
  const bool layer_ok = name.empty() || name_matches_layer(name, st->requested_layer);
  const bool shape_ok = ne0 >= st->n_tokens && ne1 >= st->n_tokens && ne2 > st->requested_head;
  if (!maybe_attn || !layer_ok || !shape_ok) {
    return true;
  }

  if (ne0 <= 0 || ne1 <= 0 || ne2 <= 0) {
    return true;
  }
  if (st->requested_head < 0 || st->requested_head >= ne2) {
    return true;
  }
  if (ne0 < st->n_tokens || ne1 < st->n_tokens) {
    return true;
  }

  const size_t bytes = ggml_nbytes(t);
  const int64_t n_elem = ggml_nelements(t);
  if (bytes == 0 || n_elem <= 0) {
    return true;
  }

  std::vector<float> raw(static_cast<size_t>(n_elem));
  ggml_backend_tensor_get(t, raw.data(), 0, bytes);

  std::vector<std::vector<double>> m(static_cast<size_t>(st->n_tokens), std::vector<double>(static_cast<size_t>(st->n_tokens), 0.0));
  auto get_val = [&](int q, int k) -> double {
    const int64_t idx = k + ne0 * (q + ne1 * st->requested_head);
    if (idx < 0 || idx >= n_elem) {
      return 0.0;
    }
    return static_cast<double>(raw[static_cast<size_t>(idx)]);
  };
  auto get_val_t = [&](int q, int k) -> double {
    const int64_t idx = q + ne0 * (k + ne1 * st->requested_head);
    if (idx < 0 || idx >= n_elem) {
      return 0.0;
    }
    return static_cast<double>(raw[static_cast<size_t>(idx)]);
  };

  double score = 0.0;
  double score_t = 0.0;
  for (int i = 0; i < st->n_tokens; ++i) {
    double row = 0.0;
    double row_t = 0.0;
    for (int j = 0; j < st->n_tokens; ++j) {
      row += get_val(i, j);
      row_t += get_val_t(i, j);
    }
    score += std::fabs(row - 1.0);
    score_t += std::fabs(row_t - 1.0);
  }
  const bool transpose = score_t < score;

  for (int i = 0; i < st->n_tokens; ++i) {
    for (int j = 0; j < st->n_tokens; ++j) {
      m[static_cast<size_t>(i)][static_cast<size_t>(j)] =
          transpose ? get_val_t(i, j) : get_val(i, j);
    }
  }

  st->captured = true;
  st->used_transpose = transpose;
  st->tensor_name = name.empty() ? op : name;
  st->shape = {ne0, ne1, ne2, ne3};
  st->matrix = std::move(m);
  return true;
}

}  // namespace

nlohmann::json extract_attention_map(const ServiceConfig& config, const AttentionRequest& request) {
  if (request.model.empty()) {
    throw std::invalid_argument("model is required");
  }
  if (request.text.empty()) {
    throw std::invalid_argument("text is required");
  }
  if (request.max_tokens < 2 || request.max_tokens > 256) {
    throw std::invalid_argument("max_tokens must be between 2 and 256");
  }

  ensure_backend();

  const std::string gguf_path =
      resolve_gguf_path(config.ollama_base_url, config.ollama_models_dir, request.model);
  llama_model* model = load_model(request.model, gguf_path);
  const llama_vocab* vocab = llama_model_get_vocab(model);

  std::vector<llama_token> tokens = tokenize(vocab, request.text, request.max_tokens);
  if (tokens.size() < 2) {
    throw std::invalid_argument("Need at least 2 tokens to build an attention map");
  }
  std::vector<std::string> pieces = token_texts(vocab, tokens);

  llama_context_params ctx_params = llama_context_default_params();
  ctx_params.n_ctx = std::max<uint32_t>(512, static_cast<uint32_t>(tokens.size() + 16));
  ctx_params.n_batch = static_cast<uint32_t>(tokens.size());
  ctx_params.n_ubatch = static_cast<uint32_t>(tokens.size());
  ctx_params.n_seq_max = 1;
  ctx_params.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_DISABLED;

  CaptureState state;
  state.requested_layer = request.layer;
  state.requested_head = request.head;
  state.n_tokens = static_cast<int>(tokens.size());
  ctx_params.cb_eval = eval_callback;
  ctx_params.cb_eval_user_data = &state;

  llama_context* ctx = llama_init_from_model(model, ctx_params);
  if (ctx == nullptr) {
    throw std::runtime_error("Failed to initialize llama_context for attention extraction");
  }

  llama_batch batch = llama_batch_get_one(tokens.data(), static_cast<int32_t>(tokens.size()));
  const int decode_rc = llama_decode(ctx, batch);
  llama_free(ctx);

  if (decode_rc != 0) {
    throw std::runtime_error("llama_decode failed during attention extraction");
  }

  nlohmann::json tok_json = nlohmann::json::array();
  for (std::size_t i = 0; i < tokens.size(); ++i) {
    tok_json.push_back({
        {"index", i},
        {"id", tokens[i]},
        {"text", pieces[i]},
    });
  }

  if (!state.captured) {
    return {
        {"model", request.model},
        {"source", "llama_cb_eval_attention"},
        {"available", false},
        {"layer", request.layer},
        {"head", request.head},
        {"token_count", tokens.size()},
        {"tokens", tok_json},
        {"reason", "No attention tensor captured via callback on this build/model."},
        {"observed_nodes", state.observed},
    };
  }

  return {
      {"model", request.model},
      {"source", "llama_cb_eval_attention"},
      {"available", true},
      {"layer", request.layer},
      {"head", request.head},
      {"token_count", tokens.size()},
      {"tokens", tok_json},
      {"matrix", state.matrix},
      {"tensor_name", state.tensor_name},
      {"tensor_shape", state.shape},
      {"transposed_guess", state.used_transpose},
      {"note",
       "Carte d'attention extraite via cb_eval sur tenseur softmax. Selon le modèle, la couche/"
       "tête demandée peut retomber sur le meilleur match disponible."},
  };
}

}  // namespace token_viz
