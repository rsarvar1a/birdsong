from __future__ import annotations

import os
import pathlib
import typing

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


class AssetError(Exception):
    """
    An exception used by the AssetManager.
    """

    EXISTS = 0
    NOT_FOUND = 1
    NOT_FILE = 2
    NOT_DIR = 3
    ASSET_READ_ONLY = 4
    UNKNOWN_MODE = 5
    UNMANAGEABLE = 6

    def __init__(self, path, type):
        """
        Constructs the error.
        """
        self.path = path
        self.type = type
        super().__init__(self.reason())

    def reason(self):
        """
        Gets the reason.
        """
        match self.type:
            case AssetError.EXISTS:
                return "path exists: {}".format(self.path)
            case AssetError.NOT_FOUND:
                return "no such file or directory: {}".format(self.path)
            case AssetError.NOT_FILE:
                return "path is not a file: {}".format(self.path)
            case AssetError.NOT_DIR:
                return "path is not a directory: {}".format(self.path)
            case AssetError.ASSET_READ_ONLY:
                return "assets in the asset path are read-only: {}".format(self.path)
            case AssetError.UNKNOWN_MODE:
                return "invalid file mode: {}".format(self.path)
            case AssetError.UNMANAGEABLE:
                return "path is not in a managed path: {}".format(self.path)
            case _:
                return "unknown error: {}".format(self.path)


class Asset:
    """
    A wrapper for AssetManager objects that allows for context management.
    """

    READ_MODES = ["r", "rb"]
    FILE_MODES = ["r", "rb", "w", "wb"]

    def __init__(self, path: pathlib.Path, mode: str):
        """
        Opens the file.
        """
        self.file = open(path, mode)
        self.path = path

    def __enter__(self):
        """
        Provides the file.
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        Cleans up, but lets exceptions through.
        """
        self.file.close()
        return False


class AssetManager:
    """
    A wrapper for operations on the local filesystem.
    """

    def __init__(
        self, bs_inst: birdsong.Birdsong, asset_path: str, store_path: str
    ) -> None:
        """
        Configures the asset manager.
        """
        self.birdsong = bs_inst
        self.asset_path: pathlib.Path = pathlib.Path(asset_path).resolve()
        self.store_path: pathlib.Path = pathlib.Path(store_path).resolve()

    def in_asset_path(self, path: pathlib.Path) -> bool:
        """
        Determines if a path is in the asset path or not.
        """
        return path.resolve().is_relative_to(self.asset_path)

    def in_commands_path(self, path: pathlib.Path) -> bool:
        """
        Determines if a path is in the commands path or not.
        This is technically not managed by AssetManager but it
        is highly useful so we allow it.
        """
        commands_path = pathlib.Path(self.birdsong.ccmanager.commands_path).resolve()
        return path.resolve().is_relative_to(commands_path)

    def in_store_path(self, path: pathlib.Path) -> bool:
        """
        Determines if a path is in the store path or not.
        """
        return path.resolve().is_relative_to(self.store_path)

    def load_from_asset(self, file_path: str, mode: str = "r") -> Asset:
        """
        Loads an asset.
        """
        asset_path = self.translate_asset_path(file_path)

        self.test_is_file(asset_path)
        self.test_mode_read_only(asset_path, mode)

        return Asset(asset_path, mode)

    def load_precise(self, file_path: str, relative=None, mode: str = "r") -> Asset:
        """
        Returns an Asset wrapper around the requested file,by bypassing
        birdsong's configured asset and store paths. This call is extremely
        useful if you want to reference objects in terms of their location
        relative to the action file, instead of as full paths down from the
        asset and/or store path.
        """
        if relative is not None:
            relative_dir = pathlib.Path(relative).parent
            load_path = pathlib.Path(os.path.join(relative_dir, file_path)).resolve()
        else:
            load_path = pathlib.Path(file_path).resolve()

        self.test_manageable(load_path)

        if mode in Asset.READ_MODES:
            self.test_is_file(load_path)
        else:
            self.test_is_directory(load_path.parent)

        if self.in_store_path(load_path):
            self.test_mode_valid(load_path, mode)
        else:
            self.test_mode_read_only(load_path, mode)

        return Asset(load_path, mode)

    def load_from_store(self, file_path: str, mode: str = "r") -> Asset:
        """
        Loads an asset from the store path.
        """
        store_path = self.translate_store_path(file_path)

        if mode in Asset.READ_MODES:
            self.test_is_file(store_path)
        else:
            self.test_is_directory(store_path.parent)
        self.test_mode_valid(store_path, mode)

        return Asset(store_path, mode)

    def make_directory(self, dir_path: str, parents=False):
        """
        Makes a directory at the desired path in the store path.
        """
        desired_path = pathlib.Path(os.path.join(self.store_path, dir_path)).resolve()
        parent = desired_path.parent

        self.test_manageable(parent)
        self.test_not_exists(desired_path)

        if parents:
            os.makedirs(desired_path)
        else:
            self.test_is_directory(parent)
            os.mkdir(desired_path)

        self.birdsong.logger.info("created directory: {}".format(desired_path))

    def test_exists(self, path: pathlib.Path):
        """
        Tests a path to ensure it exists.
        """
        if not path.exists():
            e = AssetError(path, AssetError.NOT_FOUND)
            self.birdsong.logger.error(e.reason())
            raise e

    def test_is_directory(self, path: pathlib.Path):
        """
        Tests a path to ensure it is a directory.
        """
        self.test_exists(path)

        if not path.is_dir():
            e = AssetError(path, AssetError.NOT_DIR)
            self.birdsong.logger.error(e.reason())
            raise e

    def test_is_file(self, path: pathlib.Path):
        """
        Tests a path to ensure it is a regular file.
        """
        self.test_exists(path)

        if not path.is_file():
            e = AssetError(path, AssetError.NOT_FILE)
            self.birdsong.logger.error(e.reason())
            raise e

    def test_manageable(self, path: pathlib.Path):
        """
        Ensures the file is manageable by birdsong. This check constrains
        the abuse of load_precise to read into the larger filesystem.
        """
        if (
            (not self.in_asset_path(path))
            and (not self.in_commands_path(path))
            and (not self.in_store_path(path))
        ):
            e = AssetError(path, AssetError.UNMANAGEABLE)
            self.birdsong.logger.error(e.reason())
            raise e

    def test_mode_valid(self, path: pathlib.Path, mode: str):
        """
        Ensures the mode is valid.
        """
        if mode not in Asset.FILE_MODES:
            e = AssetError(path, AssetError.UNKNOWN_MODE)
            self.birdsong.logger.error(e.reason())
            raise e

    def test_mode_read_only(self, path: pathlib.Path, mode: str):
        """
        Ensures the file mode is read-only.
        """
        if mode not in Asset.READ_MODES:
            e = AssetError(path, AssetError.ASSET_READ_ONLY)
            self.birdsong.logger.error(e.reason())
            raise e

    def test_not_exists(self, path: pathlib.Path):
        """
        Ensures the given path does not exist.
        """
        if path.exists():
            e = AssetError(path, AssetError.EXISTS)
            self.birdsong.logger.error(e.reason())
            raise e

    def translate_asset_path(self, asset_path: str) -> pathlib.Path:
        """
        Given an asset location in the asset path, returns the absolute path.
        """
        return pathlib.Path(os.path.join(self.asset_path, asset_path))

    def translate_store_path(self, store_path: str) -> pathlib.Path:
        """
        Given an asset location in the store path, returns the absolute path.
        """
        return pathlib.Path(os.path.join(self.store_path, store_path))

    def write(self, file_path: str) -> Asset:
        """
        Returns a writeable Asset in the store path.
        """
        return self.load_from_store(file_path, mode="w")
