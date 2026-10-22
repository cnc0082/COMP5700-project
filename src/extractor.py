"""Task 1: extract key data elements (KDEs) from CIS benchmark PDFs with Gemma-3-1B."""

import hashlib
import json
import logging
import os
import re

import yaml
from pypdf import PdfReader

LLM_NAME = "google/gemma-3-1b-it"
PROMPT_TYPES = ("zero-shot", "few-shot", "chain-of-thought")
MAX_NEW_TOKENS = {"zero-shot": 24, "few-shot": 24, "chain-of-thought": 160}
CACHE_FILE = "llm-cache.json"

# A recommendation heading looks like "2.7 Ensure ... (Automated)" and may wrap onto a second line.
# The heading is captured in a lookahead so a skipped line never swallows the heading after it.
RECOMMENDATION_PATTERN = re.compile(r"^(\d+(?:\.\d+)+) (?=([^\n]+(?:\n[^\n]+)?))", re.M)
TITLE_PATTERN = re.compile(r"(.+?)\s*\((?:Automated|Manual)\)")

_generator = None


def load_documents(path1, path2):
    """Validate the two input PDFs and return [(document name, text), ...] in input order."""
    documents = []
    for path in (path1, path2):
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Document path must be a non-empty string")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Document not found: {path}")
        if not path.lower().endswith(".pdf"):
            raise ValueError(f"Document is not a PDF: {path}")
        with open(path, "rb") as f:
            if f.read(5) != b"%PDF-":
                raise ValueError(f"File does not contain PDF data: {path}")

        logging.getLogger("pypdf").setLevel(logging.ERROR)
        try:
            reader = PdfReader(path)
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as e:
            raise ValueError(f"Could not read PDF {path}: {e}") from e

        # Drop the "Page N" header so it never gets glued onto a recommendation heading.
        text = "\n".join(re.sub(r"^Page \d+\s*\n", "", page) for page in pages)
        if not text.strip():
            raise ValueError(f"PDF has no extractable text: {path}")

        name = os.path.splitext(os.path.basename(path))[0]
        documents.append((name, text))
    return documents


def build_zero_shot_prompt(document_text):
    """Return a zero-shot prompt asking for the KDE in a requirement from the document."""
    return (
        "You are a security analyst reading a CIS Docker Benchmark.\n"
        "Identify the key data element (KDE) in the security requirement below. A key data "
        "element is the Docker component, file, setting, or resource that the requirement "
        "protects or configures. Answer with only the key data element name (1-4 words).\n\n"
        f"Requirement: {document_text}"
    )


def build_few_shot_prompt(document_text):
    """Return a few-shot prompt with worked examples of KDE identification."""
    return (
        "You are a security analyst reading a CIS Docker Benchmark.\n"
        "Identify the key data element (KDE) in a security requirement: the Docker component, "
        "file, setting, or resource it protects or configures. Answer with only the key data "
        "element name.\n\n"
        "Requirement: Ensure auditing is configured for the Docker daemon\n"
        "Key data element: docker daemon\n\n"
        "Requirement: Ensure that the docker.service file ownership is set to root:root\n"
        "Key data element: docker.service file\n\n"
        "Requirement: Ensure that a user for the container has been created\n"
        "Key data element: container user\n\n"
        "Requirement: Ensure that privileged containers are not used\n"
        "Key data element: privileged container\n\n"
        f"Requirement: {document_text}\n"
        "Key data element:"
    )


def build_chain_of_thought_prompt(document_text):
    """Return a chain-of-thought prompt that walks the model through KDE identification."""
    return (
        "You are a security analyst reading a CIS Docker Benchmark.\n"
        "Identify the key data element (KDE) in the security requirement below. Think step by step:\n"
        "Step 1: Say what the requirement is about.\n"
        "Step 2: Name the Docker component, file, setting, or resource it protects or configures.\n"
        "Step 3: Shorten that name to 1-4 words. This is the key data element.\n"
        "Keep the reasoning brief. End with a final line in the form:\n"
        "FINAL ANSWER: <key data element>\n\n"
        f"Requirement: {document_text}"
    )


def parse_recommendations(document_text):
    """Return {recommendation id: title} for every recommendation heading in the text."""
    recommendations = {}
    for match in RECOMMENDATION_PATTERN.finditer(document_text):
        heading = match.group(2)
        # Table of contents entries are dot leaders, not headings.
        if "...." in heading:
            continue
        title = TITLE_PATTERN.match(heading.replace("\n", " "))
        if title:
            recommendations[match.group(1)] = " ".join(title.group(1).split())
    return dict(sorted(recommendations.items(), key=lambda item: [int(x) for x in item[0].split(".")]))


def get_generator():
    """Load Gemma-3-1B once; transformers is imported lazily so tests can run without it."""
    global _generator
    if _generator is None:
        from transformers import pipeline

        _generator = pipeline("text-generation", model=LLM_NAME, device="cpu")
    return _generator


def run_llm(prompt, prompt_type, generator=None):
    """Send one prompt to the LLM with greedy decoding and return its text reply."""
    generator = generator or get_generator()
    messages = [{"role": "user", "content": prompt}]
    output = generator(messages, max_new_tokens=MAX_NEW_TOKENS[prompt_type], do_sample=False)
    return output[0]["generated_text"][-1]["content"].strip()


def parse_element(output):
    """Pull the key data element name out of an LLM reply, or return None if there isn't one."""
    if "FINAL ANSWER" in output:
        output = output.rsplit("FINAL ANSWER", 1)[1]
    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        return None
    element = re.sub(r"^[\s:*`\"'-]*(key data element:)?", "", lines[0], flags=re.I)
    # Drop leftover list numbering ("3. ") and treat snake_case the same as spaced words.
    element = re.sub(r"^\d+[.)]\s+", "", element.strip(" .*`\"'")).replace("_", " ")
    element = " ".join(element.lower().split())
    if element.startswith("the "):
        element = element[4:]
    if not element or len(element.split()) > 6:
        return None
    return element


def load_cache(output_dir):
    path = os.path.join(output_dir, CACHE_FILE)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(output_dir, cache):
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, CACHE_FILE), "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1, sort_keys=True)


def extract_kdes(document_name, document_text, output_dir="outputs", generator=None):
    """Run every prompt type through Gemma, save the KDEs to YAML, and return (kdes, llm records).

    kdes is {element key: {"name": element name, "requirements": [requirement, ...]}}.
    Replies are cached by prompt; decoding is greedy, so a cached reply is the same one the
    model would give again.
    """
    recommendations = parse_recommendations(document_text)
    if not recommendations:
        raise ValueError(f"No recommendations found in {document_name}")

    cache = load_cache(output_dir)
    kdes = {}
    records = []
    for i, requirement in enumerate(recommendations.values(), 1):
        for prompt_type in PROMPT_TYPES:
            if prompt_type == "zero-shot":
                prompt = build_zero_shot_prompt(requirement)
            elif prompt_type == "few-shot":
                prompt = build_few_shot_prompt(requirement)
            else:
                prompt = build_chain_of_thought_prompt(requirement)
            cache_key = hashlib.sha256(f"{LLM_NAME}\n{prompt}".encode()).hexdigest()
            if cache_key not in cache:
                cache[cache_key] = run_llm(prompt, prompt_type, generator)
            output = cache[cache_key]
            records.append({
                "llm_name": LLM_NAME,
                "prompt": prompt,
                "prompt_type": prompt_type,
                "output": output,
            })
            element = parse_element(output)
            if element:
                key = re.sub(r"[^a-z0-9]+", "_", element).strip("_")
                entry = kdes.setdefault(key, {"name": element, "requirements": []})
                if requirement not in entry["requirements"]:
                    entry["requirements"].append(requirement)
        if i % 10 == 0:
            save_cache(output_dir, cache)
            print(f"  {document_name}: {i}/{len(recommendations)} requirements processed", flush=True)
    save_cache(output_dir, cache)

    for entry in kdes.values():
        entry["requirements"].sort()
    kdes = dict(sorted(kdes.items()))

    yaml_path = os.path.join(output_dir, f"{document_name}-kdes.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(kdes, f, sort_keys=True, allow_unicode=True)
    return kdes, records


def collect_llm_outputs(records, output_path):
    """Write every LLM call to a text file with LLM Name, Prompt Used, Prompt Type, LLM Output."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, record in enumerate(records, 1):
            f.write(f"===== Entry {i} =====\n")
            f.write(f"*LLM Name*\n{record['llm_name']}\n\n")
            f.write(f"*Prompt Used*\n{record['prompt']}\n\n")
            f.write(f"*Prompt Type*\n{record['prompt_type']}\n\n")
            f.write(f"*LLM Output*\n{record['output']}\n\n")
    return output_path
