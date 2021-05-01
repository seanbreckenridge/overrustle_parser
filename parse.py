import os
import re
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TextIO, NamedTuple, Iterable, List

import click
from logzero import logger  # type: ignore[import]
from pyunpack import Archive  # type: ignore[import]


class Chatlog(NamedTuple):
    dt: datetime
    username: str
    message: str
    channel: Optional[str] = None

    def serialize(self) -> Dict[str, Any]:
        return {
            "dt": int(self.dt.timestamp()),
            "username": self.username,
            "message": self.message,
            "channel": self.channel or "",
        }


Results = Iterable[Chatlog]


CHAT_REGEX = re.compile(
    r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC)\] ([^:]+):\s?(.*)"
)


def _parse_datetime(dts: str) -> datetime:
    dt = datetime.strptime(dts, r"%Y-%m-%d %H:%M:%S %Z")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    assert dt.tzinfo == timezone.utc
    return dt


def parse_chatlog(line: str, channel_name: str) -> Optional[Chatlog]:
    matches = re.match(CHAT_REGEX, line)
    if matches is None or bool(matches) is False:
        logger.debug(f"Couldnt find a match in {line}")
        return None
    return Chatlog(
        dt=_parse_datetime(matches.group(1)),
        username=matches.group(2).strip(),
        message=matches.group(3).strip(),
        channel=channel_name,
    )


def parse_chatlog_buf(f: TextIO, channel_name: str) -> Results:
    for line in f:
        c = line.strip()
        # ignore empty lines
        if len(c) == 0:
            continue
        res = parse_chatlog(c, channel_name=channel_name)
        if res is not None:
            yield res


def results_file(username: str, channel_name: str) -> Path:
    r = Path(os.getcwd(), username, channel_name + ".json")
    if not r.parent.exists():
        r.parent.mkdir()
    return r


def extract_logs_for_user(logs_dir: Path, username: str) -> None:
    assert logs_dir.exists()
    archives = sorted(list(logs_dir.rglob("*.7z")))
    assert len(archives) > 0, f"No .7z files found in {logs_dir}!"

    for archive in archives:
        channel_name = archive.stem
        resfile = results_file(username, channel_name)
        if resfile.exists():
            logger.debug(f"{resfile} already exists, skipping...")
            continue
        # files can be huge, so extracting to this directory instead of /tmp
        # in case there are space concerns
        with tempfile.TemporaryDirectory(
            prefix="temp-overrustle-", dir=os.getcwd()
        ) as td:
            logger.debug(f"Extracting {archive} to {td}")
            Archive(archive).extractall(td)
            userlogs: List[Chatlog] = []
            chatlog_files: List[Path] = list(sorted(Path(td).rglob("*.txt")))
            for i, file in enumerate(chatlog_files, 1):
                if not file.is_file():
                    continue
                logger.debug(
                    f"[{channel_name} | {i}/{len(chatlog_files)}] Processing {file.stem}..."
                )
                count = 0
                with file.open("r") as f:
                    for log in parse_chatlog_buf(f, channel_name=channel_name):
                        if log.username == username:
                            logger.debug(f"Found message {log}")
                            count += 1
                            userlogs.append(log)
                if count != 0:
                    logger.info(
                        f"found {count} chat messages by {username} in {file.stem}"
                    )
            resfile.write_text(json.dumps([l.serialize() for l in userlogs]))


@click.command(name="overrustle_parser")
@click.argument("LOGS_DIR", type=click.Path(exists=True))
@click.argument("TWITCH_USERNAME", type=str)
def main(logs_dir: str, twitch_username: str) -> None:
    extract_logs_for_user(
        logs_dir=Path(logs_dir).expanduser().absolute(), username=twitch_username
    )


def test_parse_msg() -> None:
    from io import StringIO

    MSGES = """
    [2016-04-18 00:03:38 UTC] alasdairsc: !love Justin
    [2016-04-18 00:03:38 UTC] moobot:There's 95% <3 between AlasdairSc and Justin
    """

    results = list(parse_chatlog_buf(StringIO(MSGES), channel_name=""))
    assert len(results) == 2
    msg = results[0]
    assert msg.dt == datetime(
        year=2016, month=4, day=18, hour=0, minute=3, second=38, tzinfo=timezone.utc
    )
    assert msg.username == "alasdairsc"
    assert msg.message == "!love Justin"

    assert results[1].username == "moobot"
    assert results[1].message == "There's 95% <3 between AlasdairSc and Justin"


if __name__ == "__main__":
    main()
