import re
from pathlib import Path


class MetaCred:
    """Class to read CredSweeper report item and fit value position"""

    valid_path_regex = re.compile(r"data/[0-9a-f]{8}/(src|test|other)/[0-9a-f]{8}(\.[\w-]+)?")

    def __init__(self, cs_cred: dict):
        self.rule = cs_cred["rule"]
        line_data_list = cs_cred["line_data_list"]
        path = Path(line_data_list[0]["path"])
        self.path = '/'.join([str(x) for x in path.parts[-4:]])
        if not self.path.startswith('data/'):
            # license files ...
            self.path = '/'.join([str(x) for x in path.parts[-3:]])
        assert self.path.startswith('data/'), cs_cred
        self.valid_path = bool(self.valid_path_regex.match(self.path))  # to skip license files
        line_nums = [x["line_num"] for x in line_data_list]
        self.line_start = min(line_nums)
        self.line_end = max(line_nums)
        self.value_start = line_data_list[0]["value_start"]
        self.value_end = line_data_list[0]["value_end"]
        offset = len(line_data_list[0]["line"]) - len(line_data_list[0]["line"].lstrip())
        self.strip_value_start = self.value_start - offset
        self.strip_value_end = self.value_end - offset
        self.line = line_data_list[0]["line"]
        self.variable = line_data_list[0]["variable"]
        self.value = line_data_list[0]["value"]

    def __str__(self):
        return str(self.__dict__)
