import csv
from pathlib import Path

FIELDS_TO_REMOVE = {
    'WithWords', 'InURL', 'InRuntimeParameter', 'CharacterSet',
    'VariableNameType', 'Entropy', 'Length',
    'Base64Encode', 'HexEncode', 'URLEncode'
}


def clean_csv_file(path: Path):
    if not path.suffix == ".csv":
        return
    with path.open("r", newline='', encoding="utf_8") as f:
        reader = csv.DictReader(f)
        fieldnames = [f for f in reader.fieldnames if f not in FIELDS_TO_REMOVE]
        rows = [{k: row[k] for k in fieldnames} for row in reader]

    with path.open("w", newline='', encoding="utf_8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def migrate_dir(dir_path: Path):
    for file in dir_path.glob("*.csv"):
        clean_csv_file(file)


if __name__ == "__main__":
    meta_dir = Path("meta")  # Replace with your actual path
    migrate_dir(meta_dir)
