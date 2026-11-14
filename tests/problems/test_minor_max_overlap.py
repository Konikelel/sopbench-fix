from env.domains.university.university import default_data, default_dependency_parameters
from tests import harness as H


def minors_off_the_overlap_parameter(database, parameters):
    return {name for name, minor in database["minors"].items()
            if minor["max_overlap"] != parameters["max_overlap_minor_major"]}


def test_every_task_minor_has_the_maximum_overlap_of_the_task_parameter():
    tasks = H.load_tasks("university")
    assert [t["id"] for t in tasks if minors_off_the_overlap_parameter(t["initial_database"], t["constraint_parameters"])] == []


def test_every_default_minor_has_the_default_maximum_overlap():
    assert minors_off_the_overlap_parameter(default_data, default_dependency_parameters) == set()
