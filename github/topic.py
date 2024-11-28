"""extract repo data from specific topic"""

import click
import requests
from datetime import datetime
import re
from pathlib import Path

# import pandas as pd
from parsel import Selector
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import Optional, List
import dateparser

from models import ScrapeModel

SCRIPT = "github.topic"
SCRIPT_VERSION = "0.0"
BASE_URL = "https://github.com"
US_NUMBER = re.compile(r",")


class GithubTopicModel(BaseModel):
    topic: str = Field(..., description="The name of the scraped topic")
    user: str = Field(..., description="The url to the GitHub user")
    name: str = Field(..., description="The name of the project")
    url: str = Field(..., description="The full url of the project")
    img: Optional[str] = Field(
        None, description="The source url of the project hero banner"
    )
    stars: int = Field(
        ..., description="The number of times the GitHub project has been starred"
    )
    description: Optional[str] = Field(
        ..., description="The description of the project"
    )
    tags: List[str] = Field(
        default_factory=list, description="The published list of tags of the project"
    )
    last_update: str = Field(
        ..., description="The approximate last time the project was updated"
    )
    lang: Optional[str] = Field(
        ...,
        description="The main programming language used for this project repository",
    )


Model = ScrapeModel[List[GithubTopicModel]]


@click.command("topic")
@click.argument("topic")
@click.option(
    "-m",
    "--max-pages",
    "max_pages",
    default=3,
    show_default=True,
    help="the maximum number of pages to extract from the topic",
)
@click.option(
    "-o",
    "--output",
    "out",
    default=None,
    help="if necessary, the file to output the results",
)
def run(topic, max_pages: int, out: str):
    """Scrape the topic search results from github.com"""
    res = []
    for page_url in tqdm(
        [
            f"https://github.com/topics/{topic}?page={page+1}"
            for page in range(max_pages)
        ]
    ):
        response = requests.get(page_url)
        if response.status_code == 200:
            sel = Selector(response.text)
            css_articles = "article"
            css_entry_img = "img"

            for article in tqdm(sel.css(css_articles)):
                user, name = article.css("h3>a")
                tags = list(map(str.strip, article.css("a.topic-tag::text").getall()))
                lang = article.xpath(
                    './/span[@itemprop="programmingLanguage"]/text()'
                ).get()
                description = article.css(".px-3.pt-3>p::text").get()
                res.append(
                    GithubTopicModel(
                        topic=topic,
                        user=user.css("::text").get("<NA>").strip(),
                        name=name.css("::text").get("<NA>").strip(),
                        url=BASE_URL + name.xpath("@href").get("<NA>").strip(),
                        img=article.css(css_entry_img).attrib.get("src"),
                        stars=int(
                            US_NUMBER.sub(
                                "",
                                article.xpath(
                                    './/span[@id="repo-stars-counter-star"]/@title'
                                ).get("<NA>"),
                            )
                        ),
                        description=(description is not None)
                        and description.strip()
                        or description,
                        tags=tags,
                        last_update=article.xpath(".//relative-time/@datetime")
                        .get("<NA>")
                        .strip(),
                        lang=(lang is not None) and lang.strip() or lang,
                    )
                )

    if out:
        Path(out).write_text(
            ScrapeModel[List[GithubTopicModel]](
                **{
                    "script": SCRIPT,
                    "script_version": SCRIPT_VERSION,
                    "args": list(map(str, [topic, "max_pages", max_pages])),
                    "url": page_url,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "data": res,
                }
            ).model_dump_json(indent=2)
        )
    else:
        click.echo(
            Model(
                **{
                    "script": SCRIPT,
                    "script_version": SCRIPT_VERSION,
                    "args": list(map(str, [topic, "max_pages", max_pages])),
                    "url": page_url.split("?")[0],
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "data": res,
                }
            ).model_dump_json(indent=2)
        )
