#include "model_inspect.hpp"

#include "ollama_resolve.hpp"

#include <ggml.h>
#include <gguf.h>
#include <llama.h>

#include <cmath>
#include <algorithm>
#include <cstdint>
#include <regex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace token_viz {
namespace {

uint64_t tensor_element_count(const gguf_context* ctx, int64_t tensor_id) {
  const enum ggml_type type = gguf_get_tensor_type(ctx, tensor_id);
  const size_t bytes = gguf_get_tensor_size(ctx, tensor_id);
  const size_t type_size = ggml_type_size(type);
  if (type_size == 0 || bytes == 0) {
    return 0;
  }

  const int64_t block = ggml_blck_size(type);
  if (block > 1) {
    return static_cast<uint64_t>((bytes / type_size) * static_cast<size_t>(block));
  }
  return static_cast<uint64_t>(bytes / type_size);
}

std::string tensor_category(const std::string& name) {
  if (name.find("token_embd") != std::string::npos || name.find("embd") != std::string::npos) {
    return "embedding";
  }
  if (name.find("output") != std::string::npos || name.find("lm_head") != std::string::npos) {
    return "output";
  }
  if (name.find("attn") != std::string::npos) {
    return "attention";
  }
  if (name.find("ffn") != std::string::npos || name.find("feed_forward") != std::string::npos) {
    return "ffn";
  }
  if (name.find("norm") != std::string::npos) {
    return "norm";
  }
  if (name.find("rope") != std::string::npos) {
    return "rope";
  }
  return "other";
}

int layer_index_from_name(const std::string& name) {
  static const std::regex block_re(R"(blk\.(\d+)\.)");
  std::smatch match;
  if (std::regex_search(name, match, block_re) && match.size() > 1) {
    return std::stoi(match[1].str());
  }
  if (name.find("token_embd") != std::string::npos) {
    return -2;
  }
  if (name.find("output") != std::string::npos || name.find("lm_head") != std::string::npos) {
    return -1;
  }
  return -3;
}

nlohmann::json gguf_meta_kv(const gguf_context* ctx) {
  nlohmann::json meta = nlohmann::json::object();
  const int64_t n_kv = gguf_get_n_kv(ctx);
  for (int64_t i = 0; i < n_kv; ++i) {
    const std::string key = gguf_get_key(ctx, i);
    if (key.rfind("general.", 0) == 0 || key.rfind("tokenizer.", 0) == 0 ||
        key.rfind("llama.", 0) == 0 || key.rfind("qwen", 0) == 0 ||
        key == "general.architecture") {
      const auto type = gguf_get_kv_type(ctx, i);
      if (type == GGUF_TYPE_STRING) {
        meta[key] = gguf_get_val_str(ctx, i);
      } else if (type == GGUF_TYPE_UINT32) {
        meta[key] = gguf_get_val_u32(ctx, i);
      } else if (type == GGUF_TYPE_INT32) {
        meta[key] = gguf_get_val_i32(ctx, i);
      } else if (type == GGUF_TYPE_FLOAT32) {
        meta[key] = gguf_get_val_f32(ctx, i);
      }
    }
  }
  return meta;
}

}  // namespace

nlohmann::json inspect_model(const ServiceConfig& config, const std::string& model) {
  if (model.empty()) {
    throw std::invalid_argument("model is required");
  }

  const std::string gguf_path =
      resolve_gguf_path(config.ollama_base_url, config.ollama_models_dir, model);

  gguf_init_params params{};
  params.no_alloc = true;
  params.ctx = nullptr;

  gguf_context* ctx = gguf_init_from_file(gguf_path.c_str(), params);
  if (ctx == nullptr) {
    throw std::runtime_error("Failed to open GGUF metadata: " + gguf_path);
  }

  const int64_t n_tensors = gguf_get_n_tensors(ctx);
  std::unordered_map<std::string, uint64_t> by_category;
  std::unordered_map<int, nlohmann::json> layer_map;
  nlohmann::json tensors = nlohmann::json::array();

  uint64_t total_params = 0;
  uint64_t total_bytes = 0;

  for (int64_t i = 0; i < n_tensors; ++i) {
    const char* name_c = gguf_get_tensor_name(ctx, i);
    const std::string name = name_c != nullptr ? name_c : "";
    const uint64_t elements = tensor_element_count(ctx, i);
    const size_t bytes = gguf_get_tensor_size(ctx, i);
    const std::string category = tensor_category(name);
    const int layer = layer_index_from_name(name);

    total_params += elements;
    total_bytes += bytes;
    by_category[category] += elements;

    nlohmann::json tensor = {
        {"name", name},
        {"category", category},
        {"layer", layer},
        {"elements", elements},
        {"bytes", bytes},
        {"type", static_cast<int>(gguf_get_tensor_type(ctx, i))},
    };
    tensors.push_back(tensor);

    if (layer >= -2) {
      if (layer_map.find(layer) == layer_map.end()) {
        layer_map[layer] = {
            {"layer", layer},
            {"label", layer == -2 ? "embedding" : layer == -1 ? "output" : "blk." + std::to_string(layer)},
            {"params", 0},
            {"bytes", 0},
            {"tensors", nlohmann::json::array()},
        };
      }
      layer_map[layer]["params"] = layer_map[layer]["params"].get<uint64_t>() + elements;
      layer_map[layer]["bytes"] = layer_map[layer]["bytes"].get<uint64_t>() + bytes;
      layer_map[layer]["tensors"].push_back(tensor);
    }
  }

  nlohmann::json layers = nlohmann::json::array();
  std::vector<int> layer_order;
  layer_order.reserve(layer_map.size());
  for (const auto& [layer, _] : layer_map) {
    layer_order.push_back(layer);
  }
  std::sort(layer_order.begin(), layer_order.end());
  for (const int layer : layer_order) {
    layers.push_back(layer_map[layer]);
  }

  nlohmann::json categories = nlohmann::json::object();
  for (const auto& [cat, count] : by_category) {
    categories[cat] = {
        {"params", count},
        {"share", total_params > 0 ? static_cast<double>(count) / static_cast<double>(total_params) : 0.0},
    };
  }

  const nlohmann::json metadata = gguf_meta_kv(ctx);

  char model_desc[256] = {};
  uint64_t llama_params = 0;
  uint64_t llama_bytes = 0;

  llama_backend_init();
  llama_model_params mparams = llama_model_default_params();
  mparams.vocab_only = true;
  mparams.use_mmap = true;
  llama_model* llama_model_ptr = llama_model_load_from_file(gguf_path.c_str(), mparams);
  if (llama_model_ptr != nullptr) {
    llama_model_desc(llama_model_ptr, model_desc, sizeof(model_desc));
    llama_params = llama_model_n_params(llama_model_ptr);
    llama_bytes = llama_model_size(llama_model_ptr);
    llama_model_free(llama_model_ptr);
  }

  gguf_free(ctx);

  return {
      {"model", model},
      {"gguf_path", gguf_path},
      {"source", "gguf_metadata"},
      {"visualization_note",
       "Carte structurelle du modele (tenseurs / blocs). Les 1.5B parametres ne sont pas "
       "affichables un par un — chaque boite represente un tenseur entier (millions de poids)."},
      {"total_params_gguf", total_params},
      {"total_params_llama", llama_params},
      {"total_bytes_gguf", total_bytes},
      {"total_bytes_llama", llama_bytes},
      {"model_desc", std::string(model_desc)},
      {"tensor_count", n_tensors},
      {"categories", categories},
      {"layers", layers},
      {"tensors", tensors},
      {"metadata", metadata},
  };
}

}  // namespace token_viz
