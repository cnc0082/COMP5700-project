import json
import os
import subprocess
import zipfile

import pandas as pd

# dockerfiles per hadolint call
# marks a finished unzip
BATCH_SIZE = 200
DONE_MARKER = ".extracted"


rules = {
         "user for the container": ["DL3002", "DL3004"],
         "trusted base images": ["DL3006", "DL3007"],
         "unnecessary packages": ["DL3015", "DL3001"],
         "healthcheck": ["DL3057", "DL3012"],
         "update instructions": ["DL3059", "DL3009"],
         "copy is used instead of add": ["DL3020"],
         "secrets": ["DL3064"],
         "verified packages": ["DL3008", "DL3013", "DL3016", "DL3018"]
         }

# read both task 2 files into one list
def load_differences(file1, file2):
    differences = []
    with open(file1, "r", encoding="utf-8") as f:
        for line in f:
            line = line.lower().strip()
            if "no differences in regards to" in line:
                continue
            if line == "":
                continue
            differences.append(line)

    with open(file2, "r", encoding="utf-8") as f:
        for line in f:
            line = line.lower().strip()
            if "no differences in regards to" in line:
                continue
            if line == "":
                continue
            differences.append(line)


    return differences


# write the hadolint rules that match the differences
def map_differences(differences, output_path):
    found_rules = []
    for rule in rules:
        for difference in differences:
            if rule in difference:
                # add each rule once
                for rule_id in rules[rule]:
                    if rule_id not in found_rules:
                        found_rules.append(rule_id)

    with open(output_path, "w", encoding="utf-8") as f:
        if not differences:
            f.write("NO DIFFERENCES FOUND\n")
        elif not found_rules:
            f.write("NO MAPPING FOUND\n")
        else:
            for found in found_rules:
                f.write(found + "\n")
    return found_rules


# unzip the dockerfiles
def extract_dockerfiles(zip_path, extract_dir):
    if os.path.isfile(os.path.join(extract_dir, DONE_MARKER)):
        return
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name.startswith("__MACOSX") or not name.endswith(".Dockerfile"):
                continue
            with open(os.path.join(extract_dir, os.path.basename(name)), "wb") as f:
                f.write(z.read(name))
    with open(os.path.join(extract_dir, DONE_MARKER), "w") as f:
        f.write("done\n")


# run hadolint on files, None if it crashed
def scan_files(files, extract_dir):
    command = ["hadolint", "--format", "json", "--no-fail", "--warning", "DL3057"] + files
    result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", cwd=extract_dir)
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


# scan the dockerfiles, return a dataframe
def run_hadolint(rules_path, zip_path, extract_dir, limit=None):
    with open(rules_path, "r", encoding="utf-8") as f:
        content = f.read()
    rule_ids = []
    if "NO DIFFERENCES FOUND" not in content and "NO MAPPING FOUND" not in content:
        for line in content.splitlines():
            line = line.strip()
            if line != "":
                rule_ids.append(line)

    # dockerfiles to scan
    extract_dockerfiles(zip_path, extract_dir)
    names = []
    for name in sorted(os.listdir(extract_dir)):
        if name.endswith(".Dockerfile"):
            names.append(name)
    if limit is not None:
        names = names[:limit]

    rows = []
    for start in range(0, len(names), BATCH_SIZE):
        batch = names[start:start + BATCH_SIZE]
        findings = scan_files(batch, extract_dir)
        if findings is None:
            findings = []
            for name in batch:
                one = scan_files([name], extract_dir)
                if one is None:
                    print(f"  skipped (hadolint crashed): {name}", flush=True)
                else:
                    findings += one
        for finding in findings:
            if rule_ids and finding["code"] not in rule_ids:
                continue
            rows.append({
                "file": extract_dir + "/" + finding["file"],
                "code": finding["code"],
                "level": finding["level"],
                "line": finding["line"],
                "message": finding["message"],
            })
    return pd.DataFrame(rows, columns=["file", "code", "level", "line", "message"])


# count findings per file and rule, save as csv
def make_csv(df, output_path):
    counts = df.groupby(["file", "level", "code"]).size().reset_index(name="COUNT")
    counts = counts.rename(columns={"file": "FilePath", "level": "DefaultSeverity", "code": "RULEID"})
    counts = counts[["FilePath", "DefaultSeverity", "RULEID", "COUNT"]]
    counts.to_csv(output_path, index=False)
    return counts