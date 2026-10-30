from src import comparator as c

a, b = c.load_yaml_files("outputs/docker-cis-v0-kdes.yaml", "outputs/docker-cis-v1-kdes.yaml")
c.compare_element_names(a, b, "outputs/element-name-differences.txt")
c.compare_requirements(a, b, "outputs/element-requirement-differences.txt")