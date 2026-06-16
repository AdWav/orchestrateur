#pragma once

#include "config.hpp"

#include <nlohmann/json.hpp>
#include <string>

namespace token_viz {

nlohmann::json inspect_model(const ServiceConfig& config, const std::string& model);

}  // namespace token_viz
