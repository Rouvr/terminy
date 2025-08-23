
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple, cast

from .file_object import FileObject
from .directory import Directory
from .record import Record


def factory_from_dict(data: Dict[str, Any]) -> FileObject:
    """Pick the right class based on the 'type' field."""
    t = data.get("type")
    if t == "Directory":
        return Directory.from_dict(data)
    if t == "Record":
        return Record.from_dict(data)
    return FileObject.from_dict(data)


def round_trip(obj: FileObject) -> Tuple[Dict[str, Any],Dict[str, Any]]:
    """Serialize -> JSON -> deserialize (factory) -> serialize again, return both dicts for comparison."""
    first = obj.to_dict()
    blob = json.dumps(first, indent=2)
    print(f"Serialized JSON:\n{blob}\n")
    again = json.loads(blob)
    rebuilt = factory_from_dict(again)
    second = rebuilt.to_dict()
    return first, second


def assert_equal_dicts(d1: Dict[str, Any], d2: Dict[str, Any], context: str) -> None:
    s1 = json.dumps(d1, sort_keys=True)
    s2 = json.dumps(d2, sort_keys=True)
    assert s1 == s2, f"{context}: mismatch after round-trip"


def make_record(name: str) -> Record:
    r = Record()
    r._name = name
    r._description = f"desc for {name}"
    r._validity_start = None  
    r._validity_end = None
    r._data_folder_path = f"/data/{name}"
    r._tags = ["sample", name]
    r._icon_path = "icons/rec.png"
    return r


def make_dir(name: str) -> Directory:
    d = Directory()
    d._icon_path = "icons/dir.png"
    return d



def test_dir_with_single_record():
    root = make_dir("root_single_rec")
    root._children = [make_record("R1")]

    first, second = round_trip(root)
    assert_equal_dicts(first, second, "Dir + 1 Record")


def test_dir_with_dir():
    root = make_dir("root_dir_dir")
    child = make_dir("childA")
    root._children = [child]

    first, second = round_trip(root)
    assert_equal_dicts(first, second, "Dir + Dir")


def test_single_dir_only():
    d = make_dir("lonely")
    first, second = round_trip(d)
    assert_equal_dicts(first, second, "Single Dir")


def test_single_record_only():
    r = make_record("lonely_record")
    first, second = round_trip(r)
    assert_equal_dicts(first, second, "Single Record")


def test_mixed_tree_max_10():
    """
    Build one Directory as root with up to 10 children total (mix of Directory/Record).
    Layout: 5 directories + 5 records as direct children.
    """
    root = make_dir("root10")
    dirs: List[Directory] = [make_dir(f"d{i}") for i in range(1, 6)]
    recs: List[Record] = [make_record(f"r{i}") for i in range(1, 6)]
    
    root._children = [cast(FileObject, d) for d in dirs] + [cast(FileObject, r) for r in recs]

    assert len(root._children) == 10, "Expected 10 children"

    first, second = round_trip(root)
    assert_equal_dicts(first, second, "Root with 10 children")


def main():
    # run all tests 
    tests = [
        test_dir_with_single_record,
        test_dir_with_dir,
        test_single_dir_only,
        test_single_record_only,
        test_mixed_tree_max_10,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {e}")

    print(f"\n{passed}/{len(tests)} tests passed.")


if __name__ == "__main__":
    main()
