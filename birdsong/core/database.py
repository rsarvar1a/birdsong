from __future__ import annotations

import pymongo
import typing

from urllib import parse

if typing.TYPE_CHECKING:
    from birdsong.core import birdsong


class DataManager:
    """
    A wrapper for database operations.
    """

    def __init__(
        self, bs_inst: birdsong.Birdsong, hostname: str, username: str, password: str
    ) -> None:
        """
        Creates a connection to the specified database.
        """
        self.birdsong = bs_inst
        self.handle: pymongo.MongoClient = pymongo.MongoClient(
            "mongodb://%s:%s@%s"
            % (parse.quote_plus(username), parse.quote_plus(password), hostname)
        )
