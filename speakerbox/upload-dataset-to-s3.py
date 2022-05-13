#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

import git
from quilt3 import Package

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################
# Constants

PACKAGE_NAME = "speakerbox/training-data"
TRAINING_DATA_DIRS_FOR_UPLOAD = [Path(__file__).parent / "training-data" / "diarized"]


###############################################################################
# Args


class Args(argparse.Namespace):
    def __init__(self):
        self.__parse()

    def __parse(self):
        # Setup parser
        p = argparse.ArgumentParser(
            prog="upload-dataset-to-s3",
            description="Upload the data required for training to s3.",
        )

        # Arguments
        p.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Conduct dry run of the package generation. Will create a JSON "
                "manifest file of that package instead of uploading."
            ),
        )

        # Parse
        p.parse_args(namespace=self)


###############################################################################
# Build package


def upload_dataset_for_training(dry_run: bool, force: bool) -> str:
    # Try running the download pipeline
    try:
        # Report with directory will be used for upload
        log.info(f"Using contents of directories: {TRAINING_DATA_DIRS_FOR_UPLOAD}")

        # Create quilt package
        package = Package()
        for training_data_dir in TRAINING_DATA_DIRS_FOR_UPLOAD:
            package.set_dir(training_data_dir.name, training_data_dir)

        # Report package contents
        log.info(f"Package contents: {package}")

        # Check repo status
        repo = git.Repo(search_parent_directories=True)
        if repo.is_dirty():
            if not force:
                raise ValueError(
                    "Repo has uncommitted files and force was not specified. "
                    "Commit your files before continuing."
                )
            else:
                log.warning(
                    "Repo has uncommitted files but force was specified. "
                    "I hope you know what you're doing..."
                )

        # Check for dry run
        if dry_run:
            # Attempt to build the package
            built = package.build(PACKAGE_NAME)

            # Get resolved save path
            manifest_save_path = Path("upload_manifest.jsonl").resolve()
            with open(manifest_save_path, "w") as manifest_write:
                package.dump(manifest_write)

            # Report where manifest was saved
            log.info(f"Dry run generated manifest stored to: {manifest_save_path}")
            log.info(f"Completed package dry run. Result hash: {built.top_hash}")

            return built.top_hash

        # Get current git commit
        commit = repo.head.object.hexsha

        # Upload
        pushed = package.push(
            PACKAGE_NAME,
            "s3://evamaxfield-speakerbox",
            message=f"From commit: {commit}",
        )
        log.info(f"Completed package push. Result hash: {pushed.top_hash}")
        return pushed.top_hash

    # Catch any exception
    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Runner


def main():
    args = Args()
    upload_dataset_for_training(dry_run=args.dry_run, force=args.force)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()