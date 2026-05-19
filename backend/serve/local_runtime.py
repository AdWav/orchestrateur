from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HardwareProfile(BaseModel):
    os_name: str = "windows"
    system_ram_gb: int
    gpu_vendor: str | None = None
    gpu_vram_gb: int | None = None
    cpu_threads: int | None = None


class WorkloadProfile(BaseModel):
    primary_goal: Literal[
        "developer_experience",
        "throughput",
        "compatibility",
        "benchmarking",
    ] = "developer_experience"
    concurrent_requests: int = 1
    quantized_models_only: bool = False
    fine_tuning: bool = False
    openai_compatible_api: bool = True
    target_model_sizes_b: list[float] = Field(default_factory=list)


class RuntimeRecommendation(BaseModel):
    inference_runtime: Literal["ollama", "vllm", "llama.cpp"]
    training_stack: str
    rationale: list[str]
    setup_notes: list[str]
    risks: list[str]


def recommend_runtime(
    hardware: HardwareProfile,
    workload: WorkloadProfile,
) -> RuntimeRecommendation:
    os_name = hardware.os_name.lower()
    is_windows = "win" in os_name

    training_stack = "PyTorch + Transformers + PEFT + bitsandbytes"
    rationale: list[str] = []
    setup_notes: list[str] = []
    risks: list[str] = []

    if (
        not is_windows
        and hardware.gpu_vram_gb is not None
        and hardware.gpu_vram_gb >= 24
        and workload.concurrent_requests >= 4
        and workload.primary_goal in {"throughput", "benchmarking"}
    ):
        inference_runtime: Literal["ollama", "vllm", "llama.cpp"] = "vllm"
        rationale.extend(
            [
                "La VRAM disponible permet de viser une inference plus dense et plus parallele.",
                "La charge declaree favorise un moteur optimise pour le debit et la mise en file.",
            ]
        )
        setup_notes.extend(
            [
                "Utiliser un environnement Linux pour simplifier l'exploitation de vLLM.",
                "Garder le fine-tuning hors du runtime d'inference.",
            ]
        )
        risks.append("Le support Windows de vLLM reste moins simple a operer.")
    elif workload.quantized_models_only or workload.primary_goal == "compatibility":
        inference_runtime = "llama.cpp"
        rationale.extend(
            [
                "Le besoin de compatibilite maximale favorise un runtime tres tolerant aux modeles quantises.",
                "llama.cpp reste robuste pour les configurations heterogenes ou plus modestes.",
            ]
        )
        setup_notes.extend(
            [
                "Privilegier des modeles quantises adaptes a la VRAM disponible.",
                "Utiliser ce runtime pour les agents auxiliaires ou les benchmarks de compatibilite.",
            ]
        )
        risks.append("Le debit peut rester inferieur a une stack GPU specialisee.")
    else:
        inference_runtime = "ollama"
        rationale.extend(
            [
                "Ollama offre le meilleur compromis entre simplicite de mise en route et ergonomie.",
                "Le runtime convient bien pour un orchestrateur local avec plusieurs agents dans le meme processus ou une topologie composee legere.",
            ]
        )
        setup_notes.extend(
            [
                "Standardiser les modeles exposes via une convention de nommage unique.",
                "Utiliser l'API HTTP d'Ollama comme facade simple pour l'orchestrateur.",
                "Pour une machine legere, utiliser un modele compact (ex. qwen2.5-coder:1.5b) ou qwen2.5:0.5b pour la validation plumbing.",
            ]
        )
        if hardware.system_ram_gb <= 16:
            rationale.append(
                "Sur un laptop de 16 Go de RAM, Ollama reste viable pour valider le plumbing avec des modeles tres petits."
            )
        risks.append("Le debit reste moins optimise que vLLM sur des charges tres paralleles.")

    if workload.fine_tuning:
        rationale.append("Le fine-tuning doit etre gere dans la stack Python, pas dans le runtime d'inference.")
        setup_notes.append("Preparer un pipeline separe pour les datasets, l'entrainement et l'evaluation.")
        risks.append("Ne pas coupler le fine-tuning avec le meme processus que l'orchestrateur API.")

    return RuntimeRecommendation(
        inference_runtime=inference_runtime,
        training_stack=training_stack,
        rationale=rationale,
        setup_notes=setup_notes,
        risks=risks,
    )
