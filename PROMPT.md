# Prompts

These are the prompts sent to `google/gemma-3-1b-it` in Task 1 ([src/extractor.py](src/extractor.py)).
Each recommendation title parsed from a CIS Docker Benchmark PDF (for example
`Ensure live restore is enabled`) is substituted for `{requirement}`, and every
requirement is run through all three prompts with greedy decoding.

## zero-shot

```
You are a security analyst reading a CIS Docker Benchmark.
Identify the key data element (KDE) in the security requirement below. A key data element is the Docker component, file, setting, or resource that the requirement protects or configures. Answer with only the key data element name (1-4 words).

Requirement: {requirement}
```

## few-shot

```
You are a security analyst reading a CIS Docker Benchmark.
Identify the key data element (KDE) in a security requirement: the Docker component, file, setting, or resource it protects or configures. Answer with only the key data element name.

Requirement: Ensure auditing is configured for the Docker daemon
Key data element: docker daemon

Requirement: Ensure that the docker.service file ownership is set to root:root
Key data element: docker.service file

Requirement: Ensure that a user for the container has been created
Key data element: container user

Requirement: Ensure that privileged containers are not used
Key data element: privileged container

Requirement: {requirement}
Key data element:
```

## chain-of-thought

```
You are a security analyst reading a CIS Docker Benchmark.
Identify the key data element (KDE) in the security requirement below. Think step by step:
Step 1: Say what the requirement is about.
Step 2: Name the Docker component, file, setting, or resource it protects or configures.
Step 3: Shorten that name to 1-4 words. This is the key data element.
Keep the reasoning brief. End with a final line in the form:
FINAL ANSWER: <key data element>

Requirement: {requirement}
```
