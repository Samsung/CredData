from typing import Tuple, Union

from meta_row import MetaRow


class MetaKey:
    def __init__(self, meta_file_path: Union[MetaRow, str], line_start: int, line_end: int):
        if isinstance(meta_file_path, MetaRow):
            self.key: Tuple[str, int, int] = (meta_file_path.FilePath, meta_file_path.LineStart, meta_file_path.LineEnd)
        elif isinstance(meta_file_path, str) and isinstance(line_start, int) and isinstance(line_end, int):
            if line_start > line_end:
                raise RuntimeError(f"Wrong start-end values {line_start} > {line_end}")
            self.key: Tuple[str, int, int] = (meta_file_path, line_start, line_end)
        else:
            raise RuntimeError(f"Wrong values {meta_file_path}, {line_start}, {line_end}")

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other: 'MetaKey'):
        return self.key == other.key

    def __ne__(self, other: 'MetaKey'):
        return not (self == other)
