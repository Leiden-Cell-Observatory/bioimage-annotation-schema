"""Command line: ``bas validate``, ``bas ro-crate``, ``bas bia``.

Each command takes an annotation set's folder (holding annotation-set.yaml and
annotation-records.csv), so tools in any language can use the exports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .io import SchemaError, read_records, read_set


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bas", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="check a set's documents").add_argument("folder", type=Path)
    commands.add_parser("ro-crate", help="write ro-crate-metadata.json").add_argument("folder", type=Path)
    bia = commands.add_parser("bia", help="build a BioImage Archive bundle with MIFA metadata")
    bia.add_argument("folder", type=Path)
    bia.add_argument("dest", type=Path)
    bia.add_argument("--accession")
    args = parser.parse_args(argv)

    try:
        annotation_set, records = read_set(args.folder), read_records(args.folder)
    except SchemaError as error:
        print(error, file=sys.stderr)
        return 1
    if args.command == "validate":
        print(f"OK: {annotation_set.name}, {len(records)} records")
    elif args.command == "ro-crate":
        from .crate import write_ro_crate

        print(write_ro_crate(annotation_set, records, args.folder))
    else:
        from .mifa import save_bia_package

        result = save_bia_package(annotation_set, records, args.folder, args.dest, accession=args.accession)
        print(f"{result['dir']}: {result['n_annotations']} annotations, {result['copied']} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
