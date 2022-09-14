from dataclasses import dataclass, field
from enum import Enum, auto
from ratelimiter import RateLimiter
from typing import Any, List, Optional, Set
from urllib.robotparser import RobotFileParser

import boto3
import lxml.etree
import marshmallow_dataclass
import os
import requests
import sys
import traceback
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
    # Default rate limit is 10 RPS
    max_calls: int = 10
    period: int = 1
    robot_policy: Optional[RobotPolicy] = None
    sitemap: Optional[str] = None
    atom: Optional[str] = None
    pages: List[Page] = field(default_factory=list)


SiteSchema = marshmallow_dataclass.class_schema(Site)()


def schema_filename(sname: str) -> str:
    return os.path.join(os.path.dirname(__file__), f'schemas/{sname}.xsd')


class Crawler:
    @classmethod
    def new(cls, site: Site, rate_limiter: Any) -> 'Crawler':
        robot_parser: Optional[RobotFileParser] = None
        if site.robot_policy is not None:
            robot_url = urllib.parse.urljoin(site.base_url, 'robots.txt')
            print('Reading robots.txt from', robot_url)
            robot_parser = RobotFileParser(robot_url)
            with rate_limiter:
                robot_parser.read()
            # TODO(ejconlon) Update to py3.8 and use this
            # sitemaps = robot_parser.site_maps()
            # if site.sitemap is None:
            #     assert sitemaps is None, 'should have no sitemap'
            # else:
            #     expected_sitemap = urllib.parse.urljoin(site.base_url, site.sitemap)
            #     assert sitemaps == [expected_sitemap], 'should have sitemap'
        return cls(
            base_url=site.base_url,
            robot_policy=site.robot_policy,
            robot_parser=robot_parser,
            rate_limiter=rate_limiter
        )

    def __init__(
        self,
        base_url: str,
        robot_policy: Optional[RobotPolicy],
        robot_parser: Optional[RobotFileParser],
        rate_limiter: Any
    ) -> None:
        self._base_url = base_url
        self._robot_policy = robot_policy
        self._robot_parser = robot_parser
        self._seen_urls: Set[str] = set()
        self._rate_limiter = rate_limiter

    def has_crawled(self, url: str) -> bool:
        if url in self._seen_urls:
            return True
        elif not url.endswith('.html'):
            expanded_url = urllib.parse.urljoin(url, 'index.html')
            return expanded_url in self._seen_urls
        else:
            return False

    def crawl_page(self, page: Page) -> None:
        url = urllib.parse.urljoin(self._base_url, page.path)
        self.crawl_url(url)

    def crawl_url(self, url: str) -> None:
        print('Testing page', url)
        with self._rate_limiter:
            res = requests.head(url)
        res.raise_for_status()
        if self._robot_parser is not None:
            can_fetch = self._robot_parser.can_fetch('*', url)
            if self._robot_policy == RobotPolicy.deny:
                assert not can_fetch, 'should deny'
            else:
                assert can_fetch, 'should allow'
        self._seen_urls.add(url)

    def load_xml(self, sname: str, path: str) -> Any:
        schema = lxml.etree.XMLSchema(file=schema_filename(sname))
        assert schema is not None
        url = urllib.parse.urljoin(self._base_url, path)
        with self._rate_limiter:
            res = requests.get(url)
        res.raise_for_status()
        tree = lxml.etree.fromstring(res.text.encode())
        schema.assertValid(tree)
        return tree


def recrawl(site: Site) -> None:
    print('Starting site', site.base_url)

    rate_limiter = RateLimiter(max_calls=site.max_calls, period=site.period)

    crawler = Crawler.new(site, rate_limiter)

    for page in site.pages:
        crawler.crawl_page(page)

    sitemap_uncrawled: List[str] = []
    atom_uncrawled: List[str] = []

    if site.sitemap is not None:
        sitemap = crawler.load_xml('sitemap', site.sitemap)
        assert sitemap is not None
        urls = sitemap.xpath(
            '/x:urlset/x:url/x:loc/text()',
            namespaces={'x': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        )

        for url in urls:
            if not crawler.has_crawled(url):
                sitemap_uncrawled.append(url)

    if site.atom is not None:
        atom = crawler.load_xml('atom', site.atom)
        assert atom is not None
        urls = atom.xpath(
            '/x:feed/x:entry/x:link/@href',
            namespaces={'x': 'http://www.w3.org/2005/Atom'}
        )
        for url in urls:
            if not crawler.has_crawled(url):
                atom_uncrawled.append(url)

    for url in sitemap_uncrawled:
        print('Crawling additional sitemap url', url)
        crawler.crawl_url(url)

    for url in atom_uncrawled:
        print('Crawling additional atom url', url)
        crawler.crawl_url(url)
        break

    print('Finished site', site.base_url)


def run(fname: str) -> None:
    if fname.startswith('s3://'):
        parsed = urllib.parse.urlparse(fname)
        bucket = parsed.netloc
        key = parsed.path
        s3 = boto3.resource('s3')
        obj = s3.Object(bucket, key)
        contents = obj.get()['Body'].read().decode('utf-8')
    else:
        with open(fname, 'r') as f:
            contents = f.read()
    raw_sites = list(yaml.safe_load_all(contents))
    sites = [SiteSchema.load(r) for r in raw_sites]
    for site in sites:
        recrawl(site)


def handler() -> None:
    fname = os.environ['RECRAWLER_CONFIG']
    topic_arn = os.environ.get('ALERT_TOPIC_ARN')
    try:
        run(fname)
    except Exception:
        if topic_arn is not None:
            message = traceback.format_exc()
            sns = boto3.client('sns')
            sns.publish(
                TopicArn=topic_arn,
                Subject='Recrawler FAILED',
                Message=message
            )
        raise


def main() -> None:
    assert len(sys.argv) <= 2
    if len(sys.argv) == 2:
        fname = sys.argv[1]
        os.environ['RECRAWLER_CONFIG'] = fname
    handler()


if __name__ == '__main__':
    main()
