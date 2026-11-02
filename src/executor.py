import json
import os
import subprocess
import zipfile

import pandas as pd

# how many dockerfiles to give hadolint at once (windows limits command length)
BATCH_SIZE = 200
# file that shows the zip was fully unzipped
DONE_MARKER = ".extracted"

# CIS keyword -> hadolint rules that match it
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

# read the two task 2 text files into one list of differences
def load_differences(file1, file2):
    differences = []
    with open(file1, "r", encoding="utf-8") as f:
        for line in f:
            line = line.lower().strip()
            # skip the no differences message and blank lines
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


# find the hadolint rules that match the differences and write them to a text file
def map_differences(differences, output_path):
    found_rules = []
    for rule in rules:
        for difference in differences:
            if rule in difference:
                # add each matching rule once
                for rule_id in rules[rule]:
                    if rule_id not in found_rules:
                        found_rules.append(rule_id)

    with open(output_path, "w", encoding="utf-8") as f:
        if found_rules:
            for found in found_rules:
                f.write(found + "\n")
        else:
            f.write("NO DIFFERENCES FOUND\n")
    return found_rules


# unzip the dockerfiles into a folder
def extract_dockerfiles(zip_path, extract_dir):
    # already unzipped, skip it
    if os.path.isfile(os.path.join(extract_dir, DONE_MARKER)):
        return
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            # skip mac junk files
            if name.startswith("__MACOSX") or not name.endswith(".Dockerfile"):
                continue
            with open(os.path.join(extract_dir, os.path.basename(name)), "wb") as f:
                f.write(z.read(name))
    with open(os.path.join(extract_dir, DONE_MARKER), "w") as f:
        f.write("done\n")


# run hadolint on the dockerfiles and return the results as a dataframe
def run_hadolint(rules_path, zip_path, extract_dir, limit=None):
    # get the rule ids from the text file (empty list means all rules)
    with open(rules_path, "r", encoding="utf-8") as f:
        content = f.read()
    rule_ids = []
    if "NO DIFFERENCES FOUND" not in content:
        for line in content.splitlines():
            line = line.strip()
            if line != "":
                rule_ids.append(line)

    # get the list of dockerfiles to scan
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
        # DL3057 is off by default so turn it on
        command = ["hadolint", "--format", "json", "--no-fail", "--warning", "DL3057"]
        for name in batch:
            command.append(name)
        # run from inside the folder so the file names are short
        result = subprocess.run(command, capture_output=True, text=True, cwd=extract_dir)
        for finding in json.loads(result.stdout):
            # only keep the rules we want
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
