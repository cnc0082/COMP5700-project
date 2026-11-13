# comp5700-project

## Team Members

| Name | Email ID | Banner ID |
|------|----------|-----------|
| Chase Childers | cnc0082@auburn.edu | 902732826 |
| Woosol Kim | wzk0029@auburn.edu | 904367055 |



## LLM Used
google/gemma-3-1b-it

## Running the Binary
Download `comp5700.exe` from the [latest release](https://github.com/cnc0082/COMP5700-project/releases/latest) and place it in `dist/`. Hadolint must be installed and on PATH. Download `dockerfiles.zip` from the course SharePoint.

```
python -m venv comp5700-venv
comp5700-venv\Scripts\activate        (Mac/Linux: source comp5700-venv/bin/activate)
pip install -r requirements.txt
dist\comp5700.exe inputs/docker-cis-v0.pdf inputs/docker-cis-v1.pdf --zip dockerfiles.zip
```

Results are written to `outputs/`. Use `--limit N` to scan only the first N Dockerfiles. Run from the repository root so the binary finds `outputs/llm-cache.json`, which holds the saved Gemma replies for all three PDFs and skips the ~40 minute model run.

## Output Files
`outputs/hadolint-results.zip` contains `hadolint-results.csv`, the full scan of all 397,133 Dockerfiles (1,598,291 rows). It is zipped because the CSV (115 MB) is over GitHub's 100 MB file limit.

Excel only displays the first 1,048,576 rows of a sheet, so opening the CSV directly in Excel cuts it off. The file itself is complete. To see every row, load it with pandas (`pd.read_csv("hadolint-results.csv")`) or in Excel use Data → Get Data → From Text/CSV and load it to the Data Model.

## Building the Binary
PyInstaller only builds for the OS it runs on. To build on Mac/Linux, run this inside the virtual environment (output goes to `dist/comp5700`):

```
pyinstaller --noconfirm --onefile --name comp5700 --collect-all transformers --copy-metadata torch --copy-metadata tqdm --copy-metadata regex --copy-metadata safetensors --copy-metadata huggingface_hub --copy-metadata tokenizers --copy-metadata pyyaml --copy-metadata numpy --copy-metadata packaging --copy-metadata filelock --copy-metadata accelerate main.py
```