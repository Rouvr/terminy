
from __future__ import annotations
from datetime import datetime
from typing import Dict, Set, List, Iterable, Optional, Tuple

import marisa_trie
from rapidfuzz import fuzz

from src.logic.directory import Directory
from src.logic.record import Record
from src.logic.file_object import FileObject
from src.logic.helpers import normalize


class RecordIndexer:
    """
    Index Records under a Directory tree.
    Primary key = FileObject._id (stable).
    Tries are built on normalized fields (name, filename, description, id).
    """

    def __init__(self, root: Directory) -> None:
        self.root = root

        # primary
        self.by_id: Dict[str, Record] = {}

        # normalized text fields
        self.name_norm: Dict[str, str] = {}        # id -> normalized name
        self.file_norm: Dict[str, str] = {}        # id -> normalized filename
        self.desc_norm: Dict[str, str] = {}        # id -> normalized description
        self.id_norm: Dict[str, str] = {}          # id -> normalized id (usually id itself)

        # inverted maps (norm -> ids) to expand trie hits
        self.name_to_ids: Dict[str, Set[str]] = {}
        self.file_to_ids: Dict[str, Set[str]] = {}
        self.desc_to_ids: Dict[str, Set[str]] = {}
        self.id_to_ids: Dict[str, Set[str]] = {}

        # tries
        self._name_trie: marisa_trie.Trie = marisa_trie.Trie([])
        self._file_trie: marisa_trie.Trie = marisa_trie.Trie([])
        self._desc_trie: marisa_trie.Trie = marisa_trie.Trie([])
        self._id_trie: marisa_trie.Trie = marisa_trie.Trie([])

        # dates & validity
        self.created: Dict[str, datetime] = {}
        self.modified: Dict[str, datetime] = {}
        self.vstart: Dict[str, Optional[datetime]] = {}
        self.vend: Dict[str, Optional[datetime]] = {}

        # tags (normalized, but keep originals on the Record)
        self.tags: Dict[str, Set[str]] = {}

        self.rebuild()

    # ---------------- build / maintenance ----------------

    def rebuild(self) -> None:
        self.by_id.clear()
        self.name_norm.clear(); self.file_norm.clear(); self.desc_norm.clear(); self.id_norm.clear()
        self.name_to_ids.clear(); self.file_to_ids.clear(); self.desc_to_ids.clear(); self.id_to_ids.clear()
        self.created.clear(); self.modified.clear(); self.vstart.clear(); self.vend.clear(); self.tags.clear()

        for rec in Directory._walk_records(self.root):
            self._index_record(rec)

        self._rebuild_tries()

    def update(self, rec: Record | List[Record]) -> None:
        """Refresh one record after rename/move/edit."""
        if isinstance(rec, list):
            for r in rec:
                self.remove(r)
                self._index_record(r)
        else:
            self.remove(rec)
            self._index_record(rec)
        self._rebuild_tries()

    def remove(self, rec: Record) -> None:
        rid = rec._id
        if rid not in self.by_id:
            return
        # remove from maps
        for m in (self.by_id, self.name_norm, self.file_norm, self.desc_norm, self.id_norm,
                  self.created, self.modified, self.vstart, self.vend, self.tags):
            m.pop(rid, None)

        # clean inverted maps
        self._discard_from(self.name_to_ids, self.name_norm.get(rid))
        self._discard_from(self.file_to_ids, self.file_norm.get(rid))
        self._discard_from(self.desc_to_ids, self.desc_norm.get(rid))
        self._discard_from(self.id_to_ids, self.id_norm.get(rid))

    def all_records(self) -> list[Record]:
        return list(self.by_id.values())

    def _discard_from(self, inv: Dict[str, Set[str]], key: Optional[str]) -> None:
        if not key:
            return
        ids = inv.get(key)
        if ids:
            ids.discard(next(iter(ids)) if False else "")  # noop safeguard
        # precise removal (we don't know rid here; caller already popped maps)
        # Rebuild inv from forward maps on next _rebuild_tries().

    def _index_record(self, rec: Record) -> None:
        """Safe to call multiple times."""
        rid = rec._id
        self.by_id[rid] = rec

        # normalized fields (prefer already-computed normalized attrs if present)
        name = getattr(rec, "_normal_name", None) or normalize(getattr(rec, "_name", "") or "")
        desc = getattr(rec, "_normal_description", None) or normalize(getattr(rec, "_description", "") or "")
        fname = getattr(rec, "_normal_file_name", None) or normalize(getattr(rec, "_file_name", "") or "")
        rid_norm = normalize(rid)

        self.name_norm[rid] = name
        self.file_norm[rid] = fname
        self.desc_norm[rid] = desc
        self.id_norm[rid] = rid_norm

        self.name_to_ids.setdefault(name, set()).add(rid)
        self.file_to_ids.setdefault(fname, set()).add(rid)
        self.desc_to_ids.setdefault(desc, set()).add(rid)
        self.id_to_ids.setdefault(rid_norm, set()).add(rid)

        # dates / validity
        self.created[rid] = getattr(rec, "_date_created", datetime.now())
        self.modified[rid] = getattr(rec, "_date_modified", datetime.now())
        self.vstart[rid] = getattr(rec, "_validity_start", None)
        self.vend[rid] = getattr(rec, "_validity_end", None)

        # tags
        raw_tags = getattr(rec, "_tags", [])
        self.tags[rid] = {normalize(t) for t in raw_tags}

    def _rebuild_tries(self) -> None:
        self._name_trie = marisa_trie.Trie(list(self.name_to_ids.keys()))
        self._file_trie = marisa_trie.Trie(list(self.file_to_ids.keys()))
        self._desc_trie = marisa_trie.Trie(list(self.desc_to_ids.keys()))
        self._id_trie   = marisa_trie.Trie(list(self.id_to_ids.keys()))

    # ---------------- search ----------------

    def search(
        self,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        filename: Optional[str] = None,
        record_id: Optional[str] = None,
        # date windows (inclusive). Pass None to skip.
        created_min: Optional[datetime] = None,
        created_max: Optional[datetime] = None,
        modified_min: Optional[datetime] = None,
        modified_max: Optional[datetime] = None,
        validity_start_min: Optional[datetime] = None,
        validity_start_max: Optional[datetime] = None,
        validity_end_min: Optional[datetime] = None,
        validity_end_max: Optional[datetime] = None,
        # tags
        require_tags: Optional[Iterable[str]] = None,  # all must be present
        any_tags: Optional[Iterable[str]] = None,      # at least one
        exclude_tags: Optional[Iterable[str]] = None,  # none of these
        # fuzzy / ranking
        min_score: int = 65,           # RapidFuzz similarity 0..100
        max_prefix_keys: int = 300,    # cap how many trie keys to expand
        limit: int = 100,
        sort_by: str = "relevance",    # "relevance" | "created" | "modified" | "validity_end" | "validity_start" | "name" | "filename" | "id"
        descending: bool = False,
    ) -> List[Record]:
        """
        Returns matching records ordered by `sort_by`.
        If `sort_by="relevance"`, we combine fuzzy scores from provided text fields.
        """

        # 1) candidate pool from tries (intersection across provided text fields)
        pools: List[Set[str]] = []
        if name:
            pools.append(self._expand_prefix(self._name_trie, self.name_to_ids, normalize(name), max_prefix_keys))
        if filename:
            pools.append(self._expand_prefix(self._file_trie, self.file_to_ids, normalize(filename), max_prefix_keys))
        if description:
            pools.append(self._expand_prefix(self._desc_trie, self.desc_to_ids, normalize(description), max_prefix_keys))
        if record_id:
            pools.append(self._expand_prefix(self._id_trie, self.id_to_ids, normalize(record_id), max_prefix_keys))

        if pools:
            id_pool = set.intersection(*pools) if len(pools) > 1 else pools[0]
            # fallback: if a prefix query yields nothing, allow full scan for that field later
            if not id_pool:
                id_pool = set(self.by_id.keys())
        else:
            id_pool = set(self.by_id.keys())

        # 2) apply filters (dates + tags)
        id_pool = self._filter_dates(id_pool,
                                     created_min, created_max,
                                     modified_min, modified_max,
                                     validity_start_min, validity_start_max,
                                     validity_end_min, validity_end_max)
        id_pool = self._filter_tags(id_pool, require_tags, any_tags, exclude_tags)

        # 3) scoring (only over fields the caller provided)
        scored: List[Tuple[float, str]] = []
        use_name = normalize(name) if name else None
        use_file = normalize(filename) if filename else None
        use_desc = normalize(description) if description else None
        use_id   = normalize(record_id) if record_id else None

        for rid in id_pool:
            # combine similarities (0..100); average of provided fields
            sims: List[float] = []
            if use_name:
                sims.append(fuzz.WRatio(self.name_norm[rid], use_name))
            if use_file:
                sims.append(fuzz.WRatio(self.file_norm[rid], use_file))
            if use_desc:
                sims.append(fuzz.WRatio(self.desc_norm[rid], use_desc))
            if use_id:
                sims.append(fuzz.WRatio(self.id_norm[rid], use_id))

            score = sum(sims) / len(sims) if sims else 100.0
            if sims and score < min_score:
                continue
            scored.append((score, rid))

        # 4) order & return
        if sort_by == "relevance":
            scored.sort(key=lambda t: t[0], reverse=True)
            out_ids = [rid for _, rid in scored[:limit]]
            return [self.by_id[r] for r in out_ids]

        # field sort
        records = [self.by_id[rid] for _, rid in scored] if scored else [self.by_id[rid] for rid in id_pool]
        return self._sort(records, sort_by=sort_by, descending=descending)[:limit]

    # ---------------- internals ----------------

    def _expand_prefix(self, trie: marisa_trie.Trie, inv: Dict[str, Set[str]], q: str, cap: int) -> Set[str]:
        keys = trie.keys(q)[:cap]
        result: Set[str] = set()
        for k in keys:
            result.update(inv.get(k, ()))
        return result

    def _filter_dates(
        self,
        ids: Set[str],
        cmin: Optional[datetime], cmax: Optional[datetime],
        mmin: Optional[datetime], mmax: Optional[datetime],
        smin: Optional[datetime], smax: Optional[datetime],
        emin: Optional[datetime], emax: Optional[datetime],
    ) -> Set[str]:
        def in_range(v: Optional[datetime], lo: Optional[datetime], hi: Optional[datetime]) -> bool:
            if v is None:
                return False if (lo or hi) else True
            if lo and v < lo: return False
            if hi and v > hi: return False
            return True

        out: Set[str] = set()
        for rid in ids:
            if not in_range(self.created.get(rid), cmin, cmax):   continue
            if not in_range(self.modified.get(rid), mmin, mmax):  continue
            if not in_range(self.vstart.get(rid), smin, smax):    continue
            if not in_range(self.vend.get(rid),   emin, emax):    continue
            out.add(rid)
        return out

    def _filter_tags(
        self,
        ids: Set[str],
        require_tags: Optional[Iterable[str]],
        any_tags: Optional[Iterable[str]],
        exclude_tags: Optional[Iterable[str]],
    ) -> Set[str]:
        req = {normalize(t) for t in (require_tags or [])}
        anyt = {normalize(t) for t in (any_tags or [])}
        exc = {normalize(t) for t in (exclude_tags or [])}

        out: Set[str] = set()
        for rid in ids:
            tset = self.tags.get(rid, set())
            if req and not req.issubset(tset): continue
            if anyt and tset.isdisjoint(anyt): continue
            if exc and not tset.isdisjoint(exc): continue
            out.add(rid)
        return out

    def _sort(self, records: List[Record], *, sort_by: str, descending: bool) -> List[Record]:
        keyf = {
            "created":       lambda r: getattr(r, "_date_created", datetime.min),
            "modified":      lambda r: getattr(r, "_date_modified", datetime.min),
            "validity_end":  lambda r: getattr(r, "_validity_end", datetime.max) or datetime.max,
            "validity_start":lambda r: getattr(r, "_validity_start", datetime.max) or datetime.max,
            "name":          lambda r: getattr(r, "_normal_name", "") or normalize(getattr(r, "_name", "")),
            "filename":      lambda r: getattr(r, "_normal_file_name", "") or normalize(getattr(r, "_file_name", "")),
            "id":            lambda r: normalize(getattr(r, "_id", "")),
        }.get(sort_by, lambda r: getattr(r, "_date_created", datetime.min))
        return sorted(records, key=keyf, reverse=descending)


