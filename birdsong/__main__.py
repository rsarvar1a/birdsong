from __future__ import annotations

import argparse
import yaml

from birdsong.core import birdsong
from birdsong.core import utils


def main():
    """
    Birdsong's entry point.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config/config.yaml")
    cli_args = parser.parse_args()

    with open(cli_args.config, "r") as config_file:
        options = yaml.load(config_file, yaml.CLoader)

    client: birdsong.Birdsong = birdsong.Birdsong(options.get("base", {}), options.get("birdsong", {}))
    client.tweet_tweet()


if __name__ == "__main__":
    main()
