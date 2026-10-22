import os

import pytest
import yaml

from src import extractor

SAMPLE_TEXT = (
    "Table of Contents\n"
    "1.1.1 Ensure a separate partition for containers has been created (Automated) ....... 12\n"
    "1.1.1 Ensure a separate partition for containers has been created \n(Automated) \n"
    "Description: ...\n"
    "2.7 Ensure TLS authentication for Docker daemon is configured (Manual) \n"
)


class FakeGenerator:
    """Stands in for the Gemma pipeline so tests run without downloading the model."""

    def __init__(self):
        self.calls = 0

    def __call__(self, messages, **kwargs):
        self.calls += 1
        prompt = messages[-1]["content"]
        reply = "FINAL ANSWER: Docker Daemon" if "FINAL ANSWER" in prompt else "docker daemon"
        return [{"generated_text": messages + [{"role": "assistant", "content": reply}]}]


def test_load_documents(tmp_path):
    pdf = os.path.join("inputs", "docker-cis-v0.pdf")
    if os.path.isfile(pdf):
        docs = extractor.load_documents(pdf, pdf)
        assert [name for name, _ in docs] == ["docker-cis-v0", "docker-cis-v0"]
        assert "Ensure" in docs[0][1]

    with pytest.raises(FileNotFoundError):
        extractor.load_documents(str(tmp_path / "missing.pdf"), str(tmp_path / "missing.pdf"))
    not_pdf = tmp_path / "notes.txt"
    not_pdf.write_text("hello")
    with pytest.raises(ValueError):
        extractor.load_documents(str(not_pdf), str(not_pdf))
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("not really a pdf")
    with pytest.raises(ValueError):
        extractor.load_documents(str(fake_pdf), str(fake_pdf))


def test_build_zero_shot_prompt():
    prompt = extractor.build_zero_shot_prompt("Ensure live restore is enabled")
    assert isinstance(prompt, str)
    assert "key data element" in prompt
    assert prompt.endswith("Requirement: Ensure live restore is enabled")
    assert "Key data element: docker daemon" not in prompt  # no examples in zero-shot


def test_build_few_shot_prompt():
    prompt = extractor.build_few_shot_prompt("Ensure live restore is enabled")
    assert isinstance(prompt, str)
    assert prompt.count("Key data element:") == 5  # four examples plus the open slot
    assert "Requirement: Ensure live restore is enabled\nKey data element:" in prompt


def test_build_chain_of_thought_prompt():
    prompt = extractor.build_chain_of_thought_prompt("Ensure live restore is enabled")
    assert isinstance(prompt, str)
    assert "step by step" in prompt
    assert "FINAL ANSWER" in prompt
    assert "Ensure live restore is enabled" in prompt


def test_extract_kdes(tmp_path):
    generator = FakeGenerator()
    kdes, records = extractor.extract_kdes("cis-test", SAMPLE_TEXT, str(tmp_path), generator)

    assert kdes == {
        "docker_daemon": {
            "name": "docker daemon",
            "requirements": [
                "Ensure TLS authentication for Docker daemon is configured",
                "Ensure a separate partition for containers has been created",
            ],
        }
    }
    assert generator.calls == 6  # 2 requirements x 3 prompt types
    assert {r["prompt_type"] for r in records} == set(extractor.PROMPT_TYPES)
    with open(tmp_path / "cis-test-kdes.yaml", encoding="utf-8") as f:
        assert yaml.safe_load(f) == kdes

    # A second run is served from the cache without calling the model.
    extractor.extract_kdes("cis-test", SAMPLE_TEXT, str(tmp_path), generator)
    assert generator.calls == 6


def test_collect_llm_outputs(tmp_path):
    records = [{
        "llm_name": extractor.LLM_NAME,
        "prompt": "PROMPT TEXT",
        "prompt_type": "few-shot",
        "output": "docker daemon",
    }]
    path = extractor.collect_llm_outputs(records, str(tmp_path / "llm-outputs.txt"))
    content = open(path, encoding="utf-8").read()
    sections = ["*LLM Name*", "*Prompt Used*", "*Prompt Type*", "*LLM Output*"]
    positions = [content.index(s) for s in sections]
    assert positions == sorted(positions)
    for value in ["google/gemma-3-1b-it", "PROMPT TEXT", "few-shot", "docker daemon"]:
        assert value in content
