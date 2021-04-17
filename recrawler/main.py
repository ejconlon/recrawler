from dataclasses import dataclass
from enum import Enum, auto
from urllib.robotparser import RobotFileParser
from typing import List, Optional, Set

import marshmallow_dataclass
import requests
import sys
import urllib.parse
import yaml


@dataclass(frozen=True)
class Page:
    path: str


class RobotPolicy(Enum):
    deny = auto()
    allow = auto()


@dataclass(frozen=True)
class Site:
    base_url: str
    robot_policy: Optional[RobotPolicy]
    sitemap: Optional[str]
    atom: Optional[str]
    pages: List[Page]


SiteSchema = marshmallow_dataclass.class_schema(Site)()


def recrawl(site: Site) -> None:
    print('Starting site', site.base_url)

    robot_parser: Optional[RobotFileParser] = None
    if site.robot_policy is not None:
        robot_url = urllib.parse.urljoin(site.base_url, 'robots.txt')
        print('Reading robots.txt from', robot_url)
        robot_parser = RobotFileParser(robot_url)
        robot_parser.read()
        # TODO(ejconlon) Update to py3.8 and use this
        # sitemaps = robot_parser.site_maps()
        # if site.sitemap is None:
        #     assert len(sitemaps) == 0, 'should have no sitemap'
        # else:
        #     assert sitemaps == [site.sitemap], 'should have sitemap'

    seen_urls: Set[str] = set()

    for page in site.pages:
        url = urllib.parse.urljoin(site.base_url, page.path)
        print('Testing page', url)
        res = requests.head(url)
        res.raise_for_status()
        if robot_parser is not None:
            can_fetch = robot_parser.can_fetch('*', url)
            if site.robot_policy == RobotPolicy.deny:
                assert not can_fetch, 'should deny'
            else:
                assert can_fetch, 'should allow'
        seen_urls.add(url)

    print('Finished site', site.base_url)


def main() -> None:
    assert len(sys.argv) == 2
    fname = sys.argv[1]
    with open(fname, 'r') as f:
        raw_sites = list(yaml.safe_load_all(f))
    sites = [SiteSchema.load(r) for r in raw_sites]
    for site in sites:
        recrawl(site)


if __name__ == '__main__':
    main()
