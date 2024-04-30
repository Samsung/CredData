class MetaRow:
    Id: str
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
        for key, typ in self.__annotations__.items():
            if key.startswith("__"):
                continue
            row_val = row.get(key)
            if row_val is not None:
                if (typ is int or typ is float) and row_val:
                    val = typ(row_val)
                elif typ is str and isinstance(row_val, str):
                    val = row_val
                self.__setattr__(key, val)

    def __str__(self) -> str:
        dict_values = self.__dict__.values()
        _str = ','.join(str(x) for x in dict_values)
        return _str
