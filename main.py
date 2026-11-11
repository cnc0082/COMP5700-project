import argparse
import os
import sys

from src import comparator, executor, extractor


def run(pdf1, pdf2, zip_path, output_dir="outputs", limit=None):
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"Dockerfile zip not found: {zip_path}")
    os.makedirs(output_dir, exist_ok=True)

    # Task 1: extract KDEs
    records = []
    yaml_paths = []
    for name, text in extractor.load_documents(pdf1, pdf2):
        print(f"Extracting KDEs from {name} ...", flush=True)
        _, doc_records = extractor.extract_kdes(name, text, output_dir)
        records += doc_records
        yaml_paths.append(os.path.join(output_dir, f"{name}-kdes.yaml"))
    extractor.collect_llm_outputs(records, os.path.join(output_dir, "llm-outputs.txt"))

    # Task 2: compare
    print("Comparing ...", flush=True)
    kdes1, kdes2 = comparator.load_yaml_files(*yaml_paths)
    names_path = os.path.join(output_dir, "element-name-differences.txt")
    reqs_path = os.path.join(output_dir, "element-requirement-differences.txt")
    comparator.compare_element_names(kdes1, kdes2, names_path)
    comparator.compare_requirements(kdes1, kdes2, reqs_path)

    # Task 3: map to Hadolint rules, scan, write CSV
    print("Running Hadolint ...", flush=True)
    rules_path = os.path.join(output_dir, "hadolint-rules.txt")
    executor.map_differences(executor.load_differences(names_path, reqs_path), rules_path)
    df = executor.run_hadolint(rules_path, zip_path, os.path.join(output_dir, "dockerfiles"), limit)
    csv_path = os.path.join(output_dir, "hadolint-results.csv")
    executor.make_csv(df, csv_path)
    return csv_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two CIS Docker Benchmark PDFs and scan Dockerfiles.")
    parser.add_argument("pdf1")
    parser.add_argument("pdf2")
    parser.add_argument("--zip", default="dockerfiles.zip", help="Dockerfile zip (default: dockerfiles.zip)")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--limit", type=int, help="scan only this many Dockerfiles")
    args = parser.parse_args(argv)

    try:
        csv_path = run(args.pdf1, args.pdf2, args.zip, args.output_dir, args.limit)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Done. Results saved to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())