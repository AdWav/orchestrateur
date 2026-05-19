from serve.local_runtime import HardwareProfile, WorkloadProfile, recommend_runtime


def test_windows_profile_prefers_ollama_for_general_local_agents() -> None:
    recommendation = recommend_runtime(
        HardwareProfile(os_name="windows", system_ram_gb=128, gpu_vram_gb=16),
        WorkloadProfile(primary_goal="developer_experience", concurrent_requests=2),
    )

    assert recommendation.inference_runtime == "ollama"
    assert "PyTorch" in recommendation.training_stack


def test_small_laptop_validation_profile_still_prefers_ollama() -> None:
    recommendation = recommend_runtime(
        HardwareProfile(os_name="windows", system_ram_gb=16, gpu_vram_gb=None),
        WorkloadProfile(primary_goal="developer_experience", concurrent_requests=1),
    )

    assert recommendation.inference_runtime == "ollama"
    assert any("qwen2.5-coder:1.5b" in note or "qwen2.5:0.5b" in note for note in recommendation.setup_notes)


def test_large_linux_gpu_prefers_vllm_for_parallel_throughput() -> None:
    recommendation = recommend_runtime(
        HardwareProfile(os_name="linux", system_ram_gb=128, gpu_vram_gb=48),
        WorkloadProfile(primary_goal="throughput", concurrent_requests=8),
    )

    assert recommendation.inference_runtime == "vllm"


def test_low_vram_or_quantized_profile_prefers_llama_cpp() -> None:
    recommendation = recommend_runtime(
        HardwareProfile(os_name="windows", system_ram_gb=64, gpu_vram_gb=8),
        WorkloadProfile(primary_goal="compatibility", quantized_models_only=True),
    )

    assert recommendation.inference_runtime == "llama.cpp"
