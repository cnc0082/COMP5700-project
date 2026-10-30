from src import comparator

### A = old document, B = new document ###
A = {'d': {'name': 'Daemon', 'requirements': ['req1', 'req2']}}
B = {
    'd': {'name': 'Daemon', 'requirements': ['req1']},
    'f': {'name': 'Files', 'requirements': ['req3']},
}


### make two YAML files and load them ###
def test_load_yaml(tmp_path):
    text = 'd:\n name: Daemon\n requirements:\n - req1\n'
    file1 = tmp_path / 'a.yaml'
    file2 = tmp_path / 'b.yaml'
    file1.write_text(text)
    file2.write_text(text)
    kdes1, kdes2 = comparator.load_yaml_files(str(file1), str(file2))
    assert kdes1 ['d']['name'] == 'Daemon'
    assert kdes2 ['d']['requirements'] == ['req1']

def test_compare_element_names(tmp_path):
    out = tmp_path / 'names.txt'
    comparator.compare_element_names(A, B, str(out))
    assert out.read_text().strip() == 'Files'
    comparator.compare_element_names(A, A, str(out))
    assert out.read_text().strip() == 'NO DIFFERENCES IN REGARDS TO ELEMENT NAMES'


def test_compare_req(tmp_path):
    out = tmp_path / 'reqs.txt'
    comparator.compare_requirements(A, B, str(out))
    lines = out.read_text().splitlines()
    assert 'Daemon,req2' in lines
    assert 'Files,req3' in lines

    comparator.compare_requirements(A, A, str(out))
    assert out.read_text().strip() == 'NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS'