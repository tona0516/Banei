from typing import List, Dict

class Output:
    @classmethod
    def output_to_csv(cls, inputlist: List, filepath: str):
        import csv
        with open(filepath, "w") as f:
            # ヘッダー書き込み
            header: List = list(inputlist[0].keys())
            writer = csv.DictWriter(f, fieldnames=header, delimiter=',')
            writer.writeheader()

            # 値書き込み
            for row in inputlist:
                writer.writerow(row)

    @classmethod
    def output_to_json(cls, inputlist: List, filepath: str):
        import json
        with open(filepath, "w") as f:
            json.dump(inputlist, f, indent=4)