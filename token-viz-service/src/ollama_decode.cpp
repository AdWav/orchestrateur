#include "ollama_decode.hpp"

#include <curl/curl.h>

#include <cmath>
#include <algorithm>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace token_viz {
namespace {

size_t write_callback(char* ptr, size_t size, size_t nmemb, void* userdata) {
  auto* out = static_cast<std::string*>(userdata);
  out->append(ptr, size * nmemb);
  return size * nmemb;
}

std::string http_post_json(const std::string& url, const std::string& body, long timeout_sec = 300) {
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
  curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec);

  const CURLcode code = curl_easy_perform(curl);
  long status = 0;
  curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);

  curl_slist_free_all(headers);
  curl_easy_cleanup(curl);

  if (code != CURLE_OK) {
    throw std::runtime_error(std::string("Ollama HTTP error: ") + curl_easy_strerror(code));
  }
  if (status < 200 || status >= 300) {
    throw std::runtime_error("Ollama /api/generate returned HTTP " + std::to_string(status) + ": " + response);
  }

  return response;
}

double logprob_to_probability(double logprob) {
  if (!std::isfinite(logprob)) {
    return 0.0;
  }
  return std::exp(logprob);
}

std::string escape_label(const std::string& raw) {
  if (raw.empty()) {
    return "␠";
  }
  std::string out;
  out.reserve(raw.size());
  for (unsigned char ch : raw) {
    if (ch == '\n') {
      out += "↵";
    } else if (ch == '\t') {
      out += "⇥";
    } else if (ch < 32) {
      out += '?';
    } else {
      out.push_back(static_cast<char>(ch));
    }
  }
  return out;
}

struct Candidate {
  std::string token;
  double logprob = -INFINITY;
  bool selected = false;
};

std::vector<Candidate> collect_candidates(const nlohmann::json& entry) {
  std::unordered_map<std::string, Candidate> by_token;

  const std::string chosen = entry.value("token", "");
  const double chosen_logprob = entry.value("logprob", -INFINITY);
  if (!chosen.empty()) {
    by_token[chosen] = Candidate{chosen, chosen_logprob, true};
  }

  if (entry.contains("top_logprobs") && entry["top_logprobs"].is_array()) {
    for (const auto& alt : entry["top_logprobs"]) {
      const std::string token = alt.value("token", "");
      if (token.empty()) {
        continue;
      }
      const double logprob = alt.value("logprob", -INFINITY);
      auto it = by_token.find(token);
      if (it == by_token.end()) {
        by_token[token] = Candidate{token, logprob, token == chosen};
      } else {
        it->second.logprob = logprob;
        if (token == chosen) {
          it->second.selected = true;
        }
      }
    }
  }

  std::vector<Candidate> candidates;
  candidates.reserve(by_token.size());
  for (auto& [_, candidate] : by_token) {
    candidates.push_back(std::move(candidate));
  }

  std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {
    if (a.selected != b.selected) {
      return a.selected > b.selected;
    }
    return a.logprob > b.logprob;
  });

  return candidates;
}

nlohmann::json candidate_to_node(const Candidate& candidate) {
  return {
      {"name", escape_label(candidate.token)},
      {"raw", candidate.token},
      {"kind", candidate.selected ? "chosen" : "alternative"},
      {"selected", candidate.selected},
      {"logprob", candidate.logprob},
      {"probability", logprob_to_probability(candidate.logprob)},
  };
}

nlohmann::json build_step_tree(const nlohmann::json& logprobs, std::size_t step) {
  if (!logprobs.is_array() || step >= logprobs.size()) {
    return nlohmann::json::array();
  }

  const auto candidates = collect_candidates(logprobs[step]);
  nlohmann::json children = nlohmann::json::array();

  for (const auto& candidate : candidates) {
    nlohmann::json node = candidate_to_node(candidate);
    if (candidate.selected) {
      const auto deeper = build_step_tree(logprobs, step + 1);
      if (!deeper.empty()) {
        node["children"] = deeper;
      }
    }
    children.push_back(std::move(node));
  }

  return children;
}

}  // namespace

nlohmann::json build_decode_tree(const ServiceConfig& config, const DecodeTreeRequest& request) {
  if (request.model.empty()) {
    throw std::invalid_argument("model is required");
  }
  if (request.prompt.empty()) {
    throw std::invalid_argument("prompt is required");
  }
  if (request.top_logprobs < 1 || request.top_logprobs > 20) {
    throw std::invalid_argument("top_logprobs must be between 1 and 20");
  }
  if (request.num_predict < 1 || request.num_predict > 128) {
    throw std::invalid_argument("num_predict must be between 1 and 128");
  }

  std::string base = config.ollama_base_url;
  while (!base.empty() && base.back() == '/') {
    base.pop_back();
  }

  nlohmann::json body = {
      {"model", request.model},
      {"prompt", request.prompt},
      {"stream", false},
      {"logprobs", true},
      {"top_logprobs", request.top_logprobs},
      {"options", {{"num_predict", request.num_predict}}},
  };
  if (request.temperature >= 0.0) {
    body["options"]["temperature"] = request.temperature;
  }

  const std::string payload = http_post_json(base + "/api/generate", body.dump());
  const auto response = nlohmann::json::parse(payload);

  if (response.contains("error")) {
    throw std::runtime_error(response["error"].get<std::string>());
  }

  const std::string generated = response.value("response", "");
  const auto& logprobs = response.contains("logprobs") ? response["logprobs"] : nlohmann::json::array();

  nlohmann::json tree = {
      {"name", "Prompt"},
      {"kind", "prompt"},
      {"raw", request.prompt},
      {"label", escape_label(request.prompt.length() > 80
                                  ? request.prompt.substr(0, 77) + "..."
                                  : request.prompt)},
      {"children", build_step_tree(logprobs, 0)},
  };

  return {
      {"model", request.model},
      {"source", "ollama_logprobs"},
      {"top_logprobs", request.top_logprobs},
      {"num_predict", request.num_predict},
      {"response", generated},
      {"token_steps", logprobs.is_array() ? logprobs.size() : 0},
      {"tree", tree},
      {"stats",
       {
           {"prompt_eval_count", response.value("prompt_eval_count", 0)},
           {"eval_count", response.value("eval_count", 0)},
           {"eval_duration", response.value("eval_duration", 0)},
       }},
  };
}

}  // namespace token_viz
