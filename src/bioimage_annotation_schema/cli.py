"""Command line: ``bas validate``, ``bas ro-crate``, ``bas croissant``, ``bas bioimageio``, ``bas bia``.

Each command takes an annotation set's folder (holding annotation-set.yaml and
annotation-records.csv), so tools in any language can use the exports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .io import SchemaError, check_documents, read_records, read_set


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bas", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="check a set's documents")
    validate.add_argument("folder", type=Path)
    validate.add_argument("--mifa", action="store_true", help="also check MIFA's required fields")
    commands.add_parser("ro-crate", help="write ro-crate-metadata.json").add_argument("folder", type=Path)
    commands.add_parser("croissant", help="write croissant.json").add_argument("folder", type=Path)
    commands.add_parser(
        "bioimageio", help="write rdf.yaml, a bioimage.io dataset description"
    ).add_argument("folder", type=Path)
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
    if problems := check_documents(annotation_set, records):
        print("\n".join(problems), file=sys.stderr)
        return 1
    if args.command == "validate":
        print(f"OK: {annotation_set.name}, {len(records)} records")
        if args.mifa:
            from .mifa import check_mifa

            if missing := check_mifa(annotation_set):
                print("Not ready for MIFA, missing:\n- " + "\n- ".join(missing), file=sys.stderr)
                return 1
            print("Ready for MIFA")
    elif args.command == "ro-crate":
        from .crate import write_ro_crate

        print(write_ro_crate(annotation_set, records, args.folder))
    elif args.command == "croissant":
        from .croissant import CroissantNotReady, write_croissant

        try:
            print(write_croissant(annotation_set, records, args.folder))
        except CroissantNotReady as error:
            print(error, file=sys.stderr)
            return 1
    elif args.command == "bioimageio":
        from .bioimageio import BioimageioNotReady, write_bioimageio_dataset

        try:
            print(write_bioimageio_dataset(annotation_set, records, args.folder))
        except BioimageioNotReady as error:
            print(error, file=sys.stderr)
            return 1
    else:
        from .mifa import MifaNotReady, save_bia_package

        try:
            result = save_bia_package(annotation_set, records, args.folder, args.dest, accession=args.accession)
        except MifaNotReady as error:
            print(error, file=sys.stderr)
            return 1
        print(f"{result['dir']}: {result['n_annotations']} annotations, {result['copied']} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
