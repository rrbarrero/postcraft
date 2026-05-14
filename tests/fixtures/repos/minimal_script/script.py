"""A single-file script with no architecture."""

import json


def main() -> None:
    data = {"message": "hello"}
    print(json.dumps(data))


if __name__ == "__main__":
    main()
