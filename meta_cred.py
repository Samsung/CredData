import re
from pathlib import Path


class MetaCred:
    """Class to read CredSweeper report item and fit value position"""

    valid_path_regex = re.compile(r"data/[0-9a-f]{8}/(src|test|other)/[0-9a-f]{8}(\.[\w-]+)?")

    def __init__(self, cs_cred: dict):
        self.rule = cs_cred["rule"]
        line_data_list = cs_cred["line_data_list"]
        line_data_list.sort(key=lambda x: (x["line_num"], x["value_start"], x["value_end"]))
        path = Path(line_data_list[0]["path"])
        self.path = '/'.join([str(x) for x in path.parts[-4:]])
        if not self.path.startswith('data/'):
            # license files ...
            self.path = '/'.join([str(x) for x in path.parts[-3:]])
        # path for benchmark must start from "data/"
        assert self.path.startswith('data/'), cs_cred
        self.valid_path = bool(self.valid_path_regex.match(self.path))  # to skip license files

        self.line_start = line_data_list[0]["line_num"]
        self.line_end = line_data_list[-1]["line_num"]
        self.variable_start = line_data_list[0]["variable_start"]
        self.variable_end = line_data_list[-1]["variable_end"]
        self.value_start = line_data_list[0]["value_start"]
        self.value_end = line_data_list[-1]["value_end"]
        self.line = '\n'.join(x["line"] for x in line_data_list)
        self.variable = line_data_list[0]["variable"]
        self.value = line_data_list[0]["value"]

    def __str__(self):
        return str(self.__dict__)
