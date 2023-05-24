from __future__ import annotations

import pathlib
import typing

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


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
        self.asset_path: str = asset_path
        self.store_path: str = store_path
