import binascii
import csv
import dataclasses
import json
import pathlib


def main():
    with open("snapshot.json", encoding="utf_8") as f:
        snapshot = json.load(f)

    for repo_id, repo_url in snapshot.items():
        repo_id_bytes = binascii.unhexlify(repo_id)
        new_repo_id = f"{binascii.crc32(repo_id_bytes):08x}"

        meta_path = pathlib.Path("meta") / f"{new_repo_id}.csv"

        repo_meta = []
        with open(meta_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not isinstance(row, dict):
                    raise RuntimeError(f"ERROR: wrong row '{row}' in {meta_path}")
                if "Template" == row["GroundTruth"]:
                    row["GroundTruth"] = 'F'
                    if row["PredefinedPattern"]:
                        raise ValueError(str(row))
                    row["PredefinedPattern"] = "TEMPLATE"
                repo_meta.append(row)

        with open(meta_path, 'w', newline='\n') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=repo_meta[0].keys(), lineterminator='\n')
            writer.writeheader()
            for row in repo_meta:
                writer.writerow(row)


if __name__ == """__main__""":
    main()
