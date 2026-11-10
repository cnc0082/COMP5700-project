import json
import zipfile

import pandas as pd

from src import executor

def make_zip(tmp_path):
    zip_path = tmp_path / 'dockerfiles.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr ('a.Dockerfile', 'FROM ubuntu\n')
        z.writestr ('b.Dockerfile', 'FROM alpine\n')
    return str (zip_path)

class FakeResult:
    stdout = json.dumps([
        {'file': 'a.Dockerfile', 'code': 'DL3002', 'level': 'warning', 'line': 1, 'message': 'm1'},
        {'file': 'a.Dockerfile', 'code': 'DL3006', 'level': 'warning', 'line': 1, 'message': 'm2'},
    ])
 
def fake_run(*args, **kwargs):
    return FakeResult()
 
 
def test_load_differences(tmp_path):
    file1 = tmp_path / 'names.txt'
    file2 = tmp_path / 'reqs.txt'
    file1.write_text('NO DIFFERENCES IN REGARDS TO ELEMENT NAMES\n')
    file2.write_text('Daemon,Ensure a user for the container has been created\n\n')
    diffs = executor.load_differences(str(file1), str(file2))
    assert diffs == ['daemon,ensure a user for the container has been created']
 
def test_map_differences(tmp_path):
    out = tmp_path / 'rules.txt'
 
    executor.map_differences([], str(out))
    assert out.read_text().strip() == 'NO DIFFERENCES FOUND'
 
    executor.map_differences(['no matching rule here'], str(out))
    assert out.read_text().strip() == 'NO MAPPING FOUND'
 
    found = executor.map_differences(['ensure a user for the container has been created'], str(out))
    assert found == ['DL3002', 'DL3004']
    assert out.read_text().splitlines() == ['DL3002', 'DL3004']
 
 
def test_run_hadolint(tmp_path, monkeypatch):
    monkeypatch.setattr(executor.subprocess, 'run', fake_run)
    zip_path = make_zip(tmp_path)
    rules_file = tmp_path / 'rules.txt'
 
    rules_file.write_text('DL3002\n')
    df = executor.run_hadolint(str(rules_file), zip_path, str(tmp_path / 'out1'))
    assert list(df['code']) == ['DL3002']
 
    rules_file.write_text('NO MAPPING FOUND\n')
    df = executor.run_hadolint(str(rules_file), zip_path, str(tmp_path / 'out2'))
    assert sorted(df['code']) == ['DL3002', 'DL3006']
 
 
def test_make_csv(tmp_path):
    df = pd.DataFrame([
        {'file': 'a.Dockerfile', 'code': 'DL3002', 'level': 'warning', 'line': 1, 'message': 'm'},
        {'file': 'a.Dockerfile', 'code': 'DL3002', 'level': 'warning', 'line': 5, 'message': 'm'},
    ])
    out = tmp_path / 'result.csv'
    counts = executor.make_csv(df, str(out))
    assert list(counts.columns) == ['FilePath', 'DefaultSeverity', 'RULEID', 'COUNT']
    assert counts.iloc[0]['COUNT'] == 2
    assert out.read_text().splitlines()[0] == 'FilePath,DefaultSeverity,RULEID,COUNT'
 