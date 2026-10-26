"""Task 2: compare the KDE YAML files produced by Task 1."""

import os

import yaml


def load_yaml_files(path1, path2):
    """Validate and load the two KDE YAML files, returning two dictionaries."""
    kdes = []
    for path in (path1, path2):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{path} does not exist")
        if not path.lower().endswith('.yaml'):
            raise ValueError(f"{path} is not a .YAML file")
        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"{path} does not contain a KDE dictionary")
        kdes.append(data)
    return kdes[0], kdes[1]


def compare_element_names(kdes1, kdes2, output_path):
    names1 = set()
    names2 = set()
    for entry in kdes1.values():
        names1.add(entry['name'])
    for entry in kdes2.values():
        names2.add(entry['name'])
    result = names1 ^ names2
    with open(output_path, 'w', encoding='utf-8') as f:
        if not result:
            f.write("NO DIFFERENCES IN REGARDS TO ELEMENT NAMES\n")
        else:
            for name in sorted(result):
                f.write(name + "\n")
    return sorted(result)


def compare_requirements(kdes1, kdes2, output_path):
    """Write each requirement found under a KDE in only one of the two files as NAME,REQU."""
    reqs1 = {}
    reqs2 = {}
    for entry in kdes1.values():
        reqs1[entry['name']] = set(entry['requirements'])
    for entry in kdes2.values():
        reqs2[entry['name']] = set(entry['requirements'])

    # A KDE missing from one file counts as having no requirements there.
    differences = []
    for name in sorted(set(reqs1) | set(reqs2)):
        changed = reqs1.get(name, set()) ^ reqs2.get(name, set())
        for requirement in sorted(changed):
            differences.append((name, requirement))

    with open(output_path, 'w', encoding='utf-8') as f:
        if not differences:
            f.write("NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS\n")
        else:
            for name, requirement in differences:
                f.write(name + "," + requirement + "\n")
    return differences
