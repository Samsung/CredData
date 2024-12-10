import csv
import os
from pathlib import Path
from typing import Union, List, Generator


class MetaRow:
    """Class represented meta markup row structure"""

    Id: int
    FileID: str
    Domain: str
    RepoName: str
    FilePath: str
    LineStart: int
    LineEnd: int
    GroundTruth: str
    WithWords: str
    ValueStart: int
    ValueEnd: int
    InURL: str
    InRuntimeParameter: str
    CharacterSet: str
    CryptographyKey: str
    PredefinedPattern: str
    VariableNameType: str
    Entropy: float
    Length: int
    Base64Encode: str
    HexEncode: str
    URLEncode: str
    Category: str

    def __init__(self, row: dict):
        if not isinstance(row, dict) or self.__annotations__.keys() != row.keys():
            raise RuntimeError(f"ERROR: wrong row {row}")
        for key, typ in self.__annotations__.items():
            if key.startswith("__"):
                continue
            row_val = row.get(key)
            if row_val is not None:
                if typ is int:
                    if row_val:
                        val = typ(row_val)
                    else:
                        val = -1
                elif typ is float:
                    if row_val:
                        val = typ(row_val)
                    else:
                        val = 0.0
                elif typ is str and isinstance(row_val, str):
                    val = row_val
                else:
                    raise RuntimeError(f"ERROR: Unsupported {typ}")
                self.__setattr__(key, val)
        if not self.Category:
            raise RuntimeError(f"ERROR: Category must be set {row}")
        if ':' in self.Category:
            rules = self.Category.split(':')
            rule_set=set(rules)
            if len(rules) != len(rule_set):
                raise RuntimeError(f"ERROR: Each rule must be once in Category {row}")
            if "Other" in rule_set:
                raise RuntimeError(f"ERROR: 'Other' Category must be single rule in markup {row}")
        allowed_GroundTruth = ['T', 'F', "Template"]
        if self.GroundTruth not in allowed_GroundTruth:
            raise RuntimeError(f"ERROR: GroundTruth must be in {allowed_GroundTruth} {row}")
        if 0 > self.LineStart or 0 > self.LineEnd:
            raise RuntimeError(f"ERROR: LineStart and LineEnd must be positive {row}")
        elif self.LineStart > self.LineEnd:
            raise RuntimeError(f"ERROR: LineStart must be lower than LineEnd {row}")
        elif self.LineStart == self.LineEnd and 0 <= self.ValueStart and 0 <= self.ValueEnd < self.ValueStart:
            # multiline value positions are independent
            raise RuntimeError(f"ERROR: ValueStart must be lower than ValueEnd for single line {row}")

    def __str__(self) -> str:
        dict_values = self.__dict__.values()
        _str = ','.join(str(x) for x in dict_values)
        return _str

    def __repr__(self):
        return str(self)


def _meta_from_file(meta_path: Path) -> Generator[dict, None, None]:
    if ".csv" != meta_path.suffix:
        # *.csv.orig artifacts after git merge
        print(f"WARNING: skip {meta_path} file")
        return
    with open(meta_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not isinstance(row, dict):
                raise RuntimeError(f"ERROR: wrong row '{row}' in {meta_path}")
            yield row


def _meta_from_dir(meta_path: Path) -> Generator[dict, None, None]:
    for root, dirs, files in os.walk(meta_path):
        root_path = Path(root)
        for file in files:
            yield from _meta_from_file(root_path / file)
        # meta dir is flat
        break


def _get_source_gen(meta_path: Union[Path]) -> Generator[dict, None, None]:
    if not isinstance(meta_path, Path):
        raise RuntimeError(f"ERROR: unsupported source {meta_path} type {type(meta_path)}")

    if not meta_path.exists():
        raise RuntimeError(f"ERROR: {meta_path} does not exist")

    if meta_path.is_dir():
        source_gen = _meta_from_dir
    elif meta_path.is_file():
        source_gen = _meta_from_file
    else:
        raise RuntimeError(f"ERROR: unsupported {meta_path} file type")
    yield from source_gen(meta_path)


def read_meta(meta_dir: Union[str, Path]) -> List[MetaRow]:
    """Returns list of MetaRow read from file or directory. The same approach may be used to obtain a dict."""
    meta = []
    meta_ids = set()

    for row in _get_source_gen(Path(meta_dir)):
        meta_row = MetaRow(row)
        if meta_row.Id in meta_ids:
            raise RuntimeError(f"ERROR: duplicate Id row {row}")
        meta_ids.add(meta_row.Id)

        meta.append(meta_row)

    return meta
