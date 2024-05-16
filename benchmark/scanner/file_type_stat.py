import dataclasses


@dataclasses.dataclass
class FileTypeStat:
    files_number: int
    valid_lines: int
    true_markup: int
    false_markup: int
    template_markup: int
