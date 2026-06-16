#include "config.hpp"
#include "embeddings.hpp"
#include "model_inspect.hpp"
#include "ollama_decode.hpp"
#include "tokenizer.hpp"

#include <httplib.h>
#include <nlohmann/json.hpp>

#include <cstdlib>
#include <iostream>
#include <string>

namespace {

using json = nlohmann::json;

void apply_cors(httplib::Response& res, const std::vector<std::string>& origins) {
  res.set_header("Access-Control-Allow-Origin", origins.empty() ? "*" : origins.front());
  res.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.set_header("Access-Control-Allow-Headers", "Content-Type");
}

json error_json(const std::string& message) {
  return {{"detail", message}};
}

json tokenize_payload(const token_viz::TokenizeResult& result) {
  json tokens = json::array();
  for (const auto& piece : result.tokens) {
    tokens.push_back({{"id", piece.id}, {"text", piece.text}});
  }
  return {
      {"model", result.model},
      {"source", result.source},
      {"gguf_path", result.gguf_path},
      {"token_count", result.tokens.size()},
      {"tokens", tokens},
  };
}

}  // namespace

int main() {
  try {
    const token_viz::ServiceConfig config = token_viz::load_config_from_env();
    token_viz::ModelTokenizer tokenizer(config);

    httplib::Server server;

    server.Options(".*", [&](const httplib::Request& req, httplib::Response& res) {
      apply_cors(res, config.cors_origins);
      res.status = 204;
    });

    server.Get("/health", [&](const httplib::Request&, httplib::Response& res) {
      apply_cors(res, config.cors_origins);
      res.set_content(
          json({{"status", "ok"}, {"service", "token-viz-service"}}).dump(),
          "application/json");
    });

    server.Get(
        "/v1/tokenize/capabilities",
        [&](const httplib::Request&, httplib::Response& res) {
          apply_cors(res, config.cors_origins);
          res.set_content(tokenizer.capabilities().dump(), "application/json");
        });

    server.Post("/v1/tokenize", [&](const httplib::Request& req, httplib::Response& res) {
      apply_cors(res, config.cors_origins);
      try {
        const auto body = json::parse(req.body);
        const std::string model = body.value("model", "");
        const std::string text = body.value("text", body.value("content", ""));
        if (model.empty()) {
          res.status = 400;
          res.set_content(error_json("model is required").dump(), "application/json");
          return;
        }
        const auto result = tokenizer.tokenize(model, text);
        res.set_content(tokenize_payload(result).dump(), "application/json");
      } catch (const std::invalid_argument& exc) {
        res.status = 400;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      } catch (const std::exception& exc) {
        res.status = 500;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      }
    });

    server.Post(
        "/v1/tokenize/split",
        [&](const httplib::Request& req, httplib::Response& res) {
          apply_cors(res, config.cors_origins);
          try {
            const auto body = json::parse(req.body);
            const std::string model = body.value("model", "");
            const std::string input = body.value("input", body.value("prompt", ""));
            const std::string output = body.value("output", body.value("text", ""));

            if (model.empty()) {
              res.status = 400;
              res.set_content(error_json("model is required").dump(), "application/json");
              return;
            }
            if (input.empty() && output.empty()) {
              res.status = 400;
              res.set_content(
                  error_json("input or output text is required").dump(), "application/json");
              return;
            }

            json response = {{"model", model}, {"source", "llama_cpp"}};
            if (!input.empty()) {
              response["input"] = tokenize_payload(tokenizer.tokenize(model, input));
            }
            if (!output.empty()) {
              response["output"] = tokenize_payload(tokenizer.tokenize(model, output));
            }
            res.set_content(response.dump(), "application/json");
          } catch (const std::invalid_argument& exc) {
            res.status = 400;
            res.set_content(error_json(exc.what()).dump(), "application/json");
          } catch (const std::exception& exc) {
            res.status = 500;
            res.set_content(error_json(exc.what()).dump(), "application/json");
          }
        });

    server.Get("/v1/model/inspect", [&](const httplib::Request& req, httplib::Response& res) {
      apply_cors(res, config.cors_origins);
      try {
        const std::string model = req.has_param("model") ? req.get_param_value("model") : "";
        const auto payload = token_viz::inspect_model(config, model);
        res.set_content(payload.dump(), "application/json");
      } catch (const std::invalid_argument& exc) {
        res.status = 400;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      } catch (const std::exception& exc) {
        res.status = 500;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      }
    });

    server.Post("/v1/embeddings", [&](const httplib::Request& req, httplib::Response& res) {
      apply_cors(res, config.cors_origins);
      try {
        const auto body = json::parse(req.body);
        token_viz::EmbeddingsRequest emb_request;
        emb_request.model = body.value("model", "");
        emb_request.text = body.value("text", body.value("prompt", body.value("input", "")));
        emb_request.token_index = body.value("token_index", -1);
        const auto payload = token_viz::extract_embeddings(config, tokenizer, emb_request);
        res.set_content(payload.dump(), "application/json");
      } catch (const std::invalid_argument& exc) {
        res.status = 400;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      } catch (const std::exception& exc) {
        res.status = 500;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      }
    });

    server.Post("/v1/decode/tree", [&](const httplib::Request& req, httplib::Response& res) {
      apply_cors(res, config.cors_origins);
      try {
        const auto body = json::parse(req.body);
        token_viz::DecodeTreeRequest tree_request;
        tree_request.model = body.value("model", "");
        tree_request.prompt = body.value("prompt", body.value("input", ""));
        tree_request.top_logprobs = body.value("top_logprobs", 5);
        tree_request.num_predict = body.value("num_predict", 24);
        if (body.contains("temperature") && !body["temperature"].is_null()) {
          tree_request.temperature = body["temperature"].get<double>();
        }
        const auto payload = token_viz::build_decode_tree(config, tree_request);
        res.set_content(payload.dump(), "application/json");
      } catch (const std::invalid_argument& exc) {
        res.status = 400;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      } catch (const std::exception& exc) {
        res.status = 500;
        res.set_content(error_json(exc.what()).dump(), "application/json");
      }
    });

    if (!server.set_mount_point("/", config.static_dir)) {
      std::cerr << "warning: static dir not mounted: " << config.static_dir << std::endl;
    }

    std::cout << "token-viz-service listening on " << config.bind_host << ":" << config.port
              << std::endl;
    if (!server.listen(config.bind_host, config.port)) {
      std::cerr << "failed to bind " << config.bind_host << ":" << config.port << std::endl;
      return 1;
    }
    return 0;
  } catch (const std::exception& exc) {
    std::cerr << "fatal: " << exc.what() << std::endl;
    return 1;
  }
}
