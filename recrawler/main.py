from dataclasses import dataclass
from typing import List

import marshmallow_dataclass
# import requests
import sys
import yaml


@dataclass(frozen=True)
class Page:
    path: str


@dataclass(frozen=True)
class Site:
    base_url: str
    pages: List[Page]


# PageSchema = marshmallow_dataclass.class_schema(Page)
SiteSchema = marshmallow_dataclass.class_schema(Site)()


def main() -> None:
    assert len(sys.argv) == 2
    fname = sys.argv[1]
    with open(fname, 'r') as f:
        raw_sites = yaml.load_all(f)
    sites = [SiteSchema.load(r) for r in raw_sites]
    print(sites)


if __name__ == '__main__':
    main()
