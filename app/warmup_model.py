import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcriber import Transcriber  # noqa: E402


def main() -> None:
    size = sys.argv[1] if len(sys.argv) > 1 else "small"
    print(f"Modele : {size}", flush=True)
    transcriber = Transcriber(size)
    transcriber.load(on_status=lambda message: print(message, flush=True))
    print("Modele pret.", flush=True)


if __name__ == "__main__":
    main()
