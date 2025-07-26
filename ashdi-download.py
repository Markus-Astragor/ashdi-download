import os
import re
import asyncio
from contextlib import suppress
from functools import wraps
from typing import Any, Awaitable, Protocol

import asyncclick as click
from aiohttp import ClientError, ClientSession
from asyncclick_option_group import RequiredMutuallyExclusiveOptionGroup, optgroup
from bs4 import BeautifulSoup
from ffmpeg.asyncio import FFmpeg
from playwright.async_api import async_playwright


@click.command()
@optgroup.group(cls=RequiredMutuallyExclusiveOptionGroup)
@optgroup.option("-e", "--episode", metavar="URL", multiple=True)
@optgroup.option("-s", "--season", metavar="URL", multiple=True)
@click.option("-q", "--quality", type=int)
@click.option("-o", "--output-format", default="mp4")
async def cli(
    episode: list[str] | None,
    season: list[str] | None,
    quality: int,
    output_format: str,
) -> None:
    if episode:
        print(f"Starting download of episodes: {episode}")
        await download_multiple(download_episode, episode, quality, output_format)
    elif season:
        print(f"Starting download of seasons: {season}")
        await download_multiple(download_season, season, quality, output_format)


class F(Protocol):
    def __call__(
        self, *args, session: ClientSession | None = None, **kwargs
    ) -> Awaitable[Any]: ...


def aiohttp_session(f: F) -> F:
    @wraps(f)
    async def wrapper(*args, session: ClientSession | None = None, **kwargs) -> Any:
        if session:
            return await f(*args, session=session, **kwargs)

        async with ClientSession() as session:
            return await f(*args, session=session, **kwargs)

    return wrapper


@aiohttp_session
async def download_multiple(
    f: F, urls: list[str], quality: int, output_format: str, *, session: ClientSession
) -> None:
    coros = [f(url, quality, output_format, session=session) for url in urls]
    await asyncio.gather(*coros)


async def get_player_url(url: str, *, session: ClientSession = None) -> str | None:
    print(f"Fetching player URL (with JS) from: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle")

        iframe_element = await page.query_selector("iframe[src*='ashdi.vip']")
        if iframe_element:
            src = await iframe_element.get_attribute("src")
            print(f"Found iframe with src: {src}")
            await browser.close()
            return src
        
        print("Iframe with ashdi.vip not found.")
        await browser.close()
        return None


async def get_quality_url(url: str, *, session: ClientSession) -> str:
    print(f"Fetching quality URL from: {url}")
    async with session.get(url) as response:
        text = await response.text()

    bs = BeautifulSoup(text, "html.parser")
    pattern = re.compile(r'file:.*"(.*ashdi\.vip.*)"')
    tag = bs.find("script", string=pattern)
    quality_url = re.search(pattern, tag.text).group(1)
    print(f"Found quality URL: {quality_url}")
    return quality_url


async def get_episode_url(url: str, quality: int, *, session: ClientSession) -> str:
    print(f"Fetching episode URL from: {url} with quality: {quality}")
    async with session.get(url) as response:
        text = await response.text()

    url_line = next(line for line in text.splitlines() if not line.startswith("#"))

    if quality:
        begin, _, end = url_line.rsplit("/", 2)
        url_line = "/".join([begin, str(quality), end])
    print(f"Final episode URL: {url_line}")
    return url_line


async def download_playlist(url: str, output_format: str) -> None:
    _, name, _, _, _ = url.rsplit("/", 4)
    os.makedirs("downloads", exist_ok=True)
    output = f"downloads/{name}.{output_format}"
    print(f"Downloading playlist from {url} to {output}")
    ffmpeg = FFmpeg().option("y").option("nostdin").input(url).output(output, c="copy")
    await ffmpeg.execute()
    print(f"Download completed: {output}")


async def download_episode(
    url: str, quality: int, output_format: str, *, session: ClientSession
) -> None:
    with suppress(ClientError):
        print(f"Starting episode download: {url}")
        if player_url := await get_player_url(url, session=session):
            quality_url = await get_quality_url(player_url, session=session)
            episode_url = await get_episode_url(quality_url, quality, session=session)
            await download_playlist(episode_url, output_format)
        else:
            print(f"Failed to find player URL for episode: {url}")


async def get_sub_urls(url: str, *, session: ClientSession) -> list[str]:
    print(f"Fetching sub URLs for season: {url}")
    async with session.get(url) as response:
        text = await response.text()

    bs = BeautifulSoup(text, "html.parser")
    urls = [tag["href"] for tag in bs.find_all("a", href=lambda v: v.startswith(url))]
    print(f"Found sub URLs: {urls}")
    return urls


async def download_season(
    url: str, quality: int, output_format: str, *, session: ClientSession
) -> None:
    print(f"Starting season download: {url}")
    urls = await get_sub_urls(url, session=session)
    await download_multiple(
        download_episode, urls, quality, output_format, session=session
    )


if __name__ == "__main__":
    cli()
