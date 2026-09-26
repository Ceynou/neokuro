import argparse
import json
import logging
import tempfile
import uuid
import zipfile
from pathlib import Path

from neokuro.converter import generate_mokuro_volume
from neokuro.owosocket import OwocrResult, OwocrWebsocket


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".jxl")
ARCHIVE_SUFFIXES = (".cbz", ".zip")
TEMP_DIRECTORY_PREFIX = "neokuro_"
OCR_DIRECTORY_NAME = "_ocr"


def _get_volume_name(volume: Path) -> str:
    volume = volume.resolve()
    return volume.stem if volume.is_file() else volume.name


def _is_supported_archive(file: Path) -> bool:
    return file.is_file() and file.suffix.lower() in ARCHIVE_SUFFIXES


def _get_ocr_cache_dir(volume_path: Path) -> Path:
    return volume_path.parent / OCR_DIRECTORY_NAME / _get_volume_name(volume_path)


def _get_cached_page_path(ocr_cache_dir: Path, filename: str) -> Path:
    return ocr_cache_dir / f"{filename}.json"


def _load_cached_page(ocr_cache_dir: Path, filename: str) -> OwocrResult | None:
    cached_page_path = _get_cached_page_path(ocr_cache_dir, filename)
    if not cached_page_path.is_file():
        return None

    try:
        with open(cached_page_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    return {"filename": filename, "json_data": json_data}


def _save_cached_page(ocr_cache_dir: Path, result: OwocrResult) -> None:
    ocr_cache_dir.mkdir(parents=True, exist_ok=True)
    cached_page_path = _get_cached_page_path(ocr_cache_dir, result["filename"])
    with open(cached_page_path, "w", encoding="utf-8") as f:
        json.dump(result["json_data"], f, ensure_ascii=False)


def _process_directory(
    owo_socket: OwocrWebsocket,
    volume_path: Path,
    ocr_cache_dir: Path | None = None,
) -> list[OwocrResult]:
    results: list[OwocrResult] = []

    for p in sorted(volume_path.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
            if ocr_cache_dir is not None:
                cached_result = _load_cached_page(ocr_cache_dir, p.name)
                if cached_result is not None:
                    log.info(f"Using cached OCR data for {p.name}")
                    results.append(cached_result)
                    continue

            result = owo_socket.process_image(p)

            if ocr_cache_dir is not None:
                _save_cached_page(ocr_cache_dir, result)

            results.append(result)

    return results


def _process_file(
    owo_socket: OwocrWebsocket,
    volume_path: Path,
    ocr_cache_dir: Path | None = None,
) -> list[OwocrResult]:
    with tempfile.TemporaryDirectory(prefix=TEMP_DIRECTORY_PREFIX) as temp_dir:
        temp_path = Path(temp_dir)
        with zipfile.ZipFile(volume_path) as f:
            for entry in f.infolist():
                f.extract(entry, temp_path)

        return _process_directory(owo_socket, temp_path, ocr_cache_dir)


def run():
    parser = argparse.ArgumentParser(description="Mokuro manga processor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "volume",
        nargs="?",
        type=Path,
        help="Path to a single volume (directory or CBZ/ZIP file)",
    )
    group.add_argument(
        "--parent_dir",
        type=Path,
        help="Path to manga title directory containing multiple volumes",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7331,
        help="Port for the OwocrWebsocket connection (default: 7331)",
    )
    parser.add_argument(
        "--save_ocr",
        action="store_true",
        help="Save OCR data per page in a _ocr folder so interrupted runs can be resumed",
    )
    args = parser.parse_args()

    volume_paths: list[Path] = []
    metadata = dict()
    if args.volume:
        volume_paths.append(args.volume)
        metadata['title'] = _get_volume_name(args.volume)
        metadata['title_uuid'] = uuid.uuid4()
        metadata['parent_dir'] = args.volume.parent
    elif args.parent_dir:
        seen_volume_names: set[str] = set()

        # Default sort order is expected to give directories first for priority (but it's okay if that changes)
        for p in sorted(args.parent_dir.iterdir()):
            if p.name == OCR_DIRECTORY_NAME:
                continue

            if not p.is_dir() and not _is_supported_archive(p):
                continue

            volume_name = _get_volume_name(p)
            if volume_name in seen_volume_names:
                log.warning(f"Skipping duplicate volume: {p}")
                continue

            volume_paths.append(p)
            seen_volume_names.add(volume_name)

        metadata['title'] = _get_volume_name(args.parent_dir)
        metadata['title_uuid'] = uuid.uuid4()
        metadata['parent_dir'] = args.parent_dir

    log.info(f"Processing {len(volume_paths)} volume(s) for '{metadata['title']}'")

    owo_socket = OwocrWebsocket(args.port)

    for volume_path in volume_paths:
        volume_name = _get_volume_name(volume_path)
        log.info(f"Starting volume: {volume_name}")

        ocr_cache_dir = _get_ocr_cache_dir(volume_path) if args.save_ocr else None

        owocr_json_pages: list[OwocrResult] = []
        if volume_path.is_dir():
            owocr_json_pages = _process_directory(owo_socket, volume_path, ocr_cache_dir)
        elif _is_supported_archive(volume_path):
            owocr_json_pages = _process_file(owo_socket, volume_path, ocr_cache_dir)
        else:
            log.warning(f"Skipping unsupported volume: {volume_path}")
            continue

        output_mokuro_path = volume_path.parent / f"{volume_name}.mokuro"

        with open(output_mokuro_path, 'w', encoding='utf-8') as f:
            mokuro_data = generate_mokuro_volume(
                title=metadata['title'],
                title_uuid=str(metadata['title_uuid']),
                volume_name=volume_name,
                volume_json_data=owocr_json_pages,
            )
            json.dump(mokuro_data, f, ensure_ascii=False)

        log.info(f"Generated {output_mokuro_path.name}")

    log.info("All volumes successfully generated.")

    owo_socket.close()
