#pragma once

#include <string>

namespace token_viz {

// Resolve an Ollama model tag to a local GGUF blob path under ollama_models_dir.
std::string resolve_gguf_path(
    const std::string& ollama_base_url,
    const std::string& ollama_models_dir,
    const std::string& model);

}  // namespace token_viz
