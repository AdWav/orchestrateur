#include "ollama_resolve.hpp"

#include <curl/curl.h>
#include <nlohmann/json.hpp>

#include <filesystem>
#include <regex>
#include <stdexcept>
#include <string>

namespace token_viz {
namespace {

size_t write_callback(char* ptr, size_t size, size_t nmemb, void* userdata) {
  auto* out = static_cast<std::string*>(userdata);
  out->append(ptr, size * nmemb);
  return size * nmemb;
}

std::string http_post_json(const std::string& url, const std::string& body) {
  CURL* curl = curl_easy_init();
  if (curl == nullptr) {
    throw std::runtime_error("curl_easy_init failed");
  }

  std::string response;
  struct curl_slist* headers = nullptr;
  headers = curl_slist_append(headers, "Content-Type: application/json");

  curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
  curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
  curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
  curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
  curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
  curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);

  const CURLcode code = curl_easy_perform(curl);
  long status = 0;
  curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);

  curl_slist_free_all(headers);
  curl_easy_cleanup(curl);

  if (code != CURLE_OK) {
    throw std::runtime_error(std::string("Ollama HTTP error: ") + curl_easy_strerror(code));
  }
  if (status < 200 || status >= 300) {
    throw std::runtime_error("Ollama /api/show returned HTTP " + std::to_string(status));
  }

  return response;
}

}  // namespace

std::string resolve_gguf_path(
    const std::string& ollama_base_url,
    const std::string& ollama_models_dir,
    const std::string& model) {
  if (model.empty()) {
    throw std::invalid_argument("model is required");
  }

  std::string base = ollama_base_url;
  while (!base.empty() && base.back() == '/') {
    base.pop_back();
  }

  const std::string body = nlohmann::json{{"name", model}}.dump();
  const std::string payload = http_post_json(base + "/api/show", body);
  const auto json = nlohmann::json::parse(payload);

  if (!json.contains("modelfile") || !json["modelfile"].is_string()) {
    throw std::runtime_error("Ollama modelfile missing for model '" + model + "'");
  }

  const std::string modelfile = json["modelfile"].get<std::string>();
  static const std::regex from_re(R"(^FROM\s+(\S+)\s*$)", std::regex::multiline);
  std::smatch match;
  if (!std::regex_search(modelfile, match, from_re)) {
    throw std::runtime_error("No FROM entry in modelfile for model '" + model + "'");
  }

  const std::filesystem::path from_path(match[1].str());
  const std::filesystem::path blob_path =
      std::filesystem::path(ollama_models_dir) / "models" / "blobs" / from_path.filename();

  if (!std::filesystem::is_regular_file(blob_path)) {
    throw std::runtime_error(
        "GGUF blob not found for model '" + model + "': " + blob_path.string());
  }

  return blob_path.string();
}

}  // namespace token_viz
