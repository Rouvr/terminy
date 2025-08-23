# logic/make_test_data.py
from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from typing import List

from .controller import Controller                          # uses JSON load/save helpers
from .path_manager import remove_registry, set_base_path_registry  # registry ops
from .directory import Directory
from .record import Record
from .helpers import normalize

TEST_BASE = r"D:\Code\Terminy\test_data"   # <- change if you wish

def ensure_clean_test_dir(base: str) -> None:
    os.makedirs(base, exist_ok=True)
    # Start with fresh data files so we fully control the tree content
    for fname in ("data.json", "recycle_bin.json"):
        fpath = os.path.join(base, fname)
        try:
            os.remove(fpath)
        except FileNotFoundError:
            pass

def reset_registry_to(base: str) -> None:
    """
    Always delete and recreate the registry key for BasePath, per your requirement.
    """
    remove_registry(per_user=True)                 # wipe old value
    set_base_path_registry(base, per_user=True)    # set fresh value
    # Note: Controller below uses data_path directly, so this is just to keep
    # the registry consistent for future app runs or tools.

def rec(
    file_name: str,
    name: str,
    desc: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    tags: List[str] | None = None,
) -> Record:
    """Create a Record with normalized fields filled."""
    r = Record()
    r._file_name = file_name
    r._name = name
    r._description = desc
    r._validity_start = start
    r._validity_end = end
    r._tags = list(tags or [])

    # normalized variants (your Record computes these in __init__, but set explicitly
    # here to be sure they exist for later indexers/tests)
    r._normal_file_name = normalize(r._file_name)
    r._normal_name = normalize(r._name)
    r._normal_description = normalize(r._description)
    return r

def make_structure(root: Directory) -> None:
    """
    Build a small test tree (≤10 nodes under root), covering:
    - directories with nested directories
    - records with validity windows and tags
    """
    # Top-level folders
    invoices = Directory()
    invoices._file_name = "Invoices"

    contracts = Directory()
    contracts._file_name = "Contracts"

    archive = Directory()
    archive._file_name = "Archive"

    # Attach the folders
    root.inherit_children(invoices)
    root.inherit_children(contracts)
    root.inherit_children(archive)

    today = datetime.now()
    next_month = today + timedelta(days=30)
    last_month = today - timedelta(days=30)

    # Records in Invoices
    invoices_r1 = rec(
        "invoice-2025-08-001.pdf",
        "Faktura 2025-08-001",
        "Záloha za zemní práce",
        start=last_month,
        end=next_month,
        tags=["invoice", "construction"],
    )
    invoices_r2 = rec(
        "invoice-2025-08-002.pdf",
        "Faktura 2025-08-002",
        "Finální vyúčtování bagru",
        start=today,
        end=next_month,
        tags=["invoice", "machinery"],
    )
    invoices.inherit_children(invoices_r1)
    invoices.inherit_children(invoices_r2)

    # Subfolder under Contracts
    suppliers = Directory()
    suppliers._file_name = "Suppliers"
    contracts.inherit_children(suppliers)

    # Records in Contracts/Suppliers
    s1 = rec(
        "contract-supplier-ACME.pdf",
        "Smlouva s dodavatelem ACME",
        "Servisní kontrakt na stroje",
        start=last_month,
        end=None,
        tags=["contract", "service"],
    )
    suppliers.inherit_children(s1)

    # Records at root
    root_r1 = rec(
        "readme.txt",
        "Projekt Terminy",
        "Kořenový záznam s informacemi",
        tags=["meta"],
    )
    root.inherit_children(root_r1)

    # A couple archived records
    a1 = rec(
        "invoice-2024-12-099.pdf",
        "Faktura 2024-12-099",
        "Starší faktura",
        start=datetime(2024, 12, 1),
        end=datetime(2025, 1, 1),
        tags=["invoice", "archived"],
    )
    a2 = rec(
        "contract-old.pdf",
        "Smlouva stará",
        "Vypršela smlouva",
        start=datetime(2023, 1, 1),
        end=datetime(2024, 1, 1),
        tags=["contract", "archived"],
    )
    archive.inherit_children(a1)
    archive.inherit_children(a2)

def create() -> None:
    # 1) wipe & recreate registry key
    reset_registry_to(TEST_BASE)  # always delete & recreate the key. :contentReference[oaicite:2]{index=2}

    # 2) ensure clean dir and empty data files
    ensure_clean_test_dir(TEST_BASE)

    # 3) Initialize controller pointing to our test dir (JSON paths are derived here). :contentReference[oaicite:3]{index=3}
    c = Controller(data_path=TEST_BASE)

    # 4) Build a fresh structure on c.root_directory
    root = c.get_root()
    # If the JSON already contained data, we started with a clean file above.
    make_structure(root)

    # 5) Persist to disk
    c.save_state()

    print(f"[OK] Test data written to: {TEST_BASE}")
    print(f"[OK] Registry key reset to: {TEST_BASE} (Software\\Terminy\\BasePath)")
    print(f"[OK] Files: {os.path.join(TEST_BASE, 'data.json')} | {os.path.join(TEST_BASE, 'recycle_bin.json')}")



def print_thing():
    c = Controller(data_path=TEST_BASE)
    root = c.get_root()
    root.print_children()
    

if __name__ == "__main__":
    print_thing()
    
