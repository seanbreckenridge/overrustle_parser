# overrustle_parser

Some code to extract my messages from [this overrustle logs archive torrent](https://www.reddit.com/r/Destiny/comments/gcapu0/overrustle_logs_archive_torrent_as_of_april_30/). For those unaware, OverRustle collated logs from popular twitch channels for a couple years but were shut down in 2020 -- so this is just to grab some of my old messages so I have access to them.

Thought the [twitch data request](https://www.twitch.tv/p/en/legal/privacy-choices/#user-privacy-requests) would've given me my chat logs but sadly did not.

Expects:

- the logs directory (which has a bunch of `.7z` files in it) as the first argument
- your twitch username as the second argument

Extracts the `.7z` files one by one into the current directory, finds any of my logs, then removes the temporary directory. Can take multiple days to run depending on your computer, is a *lot* of data (`~48G` when compressed)

Saves results to a `./<your username>` directory -- one JSON file per channel. This saves even if it finds no logs, so in case this crashes, it can re-started and already processed files will be skipped. To combine those into a single file, you can use [`jq`](https://github.com/stedolan/jq), like `jq '.[]' <./<your username>/* | jq -r --slurp > comments.json`

Created to be used as part of [HPI](https://github.com/seanbreckenridge/HPI)

### Example Usage

```bash
git clone https://github.com/seanbreckenridge/overrustle_parser
cd ./overrustle_parser
python3 -m pip install -r ./requirements.txt
python3 parse.py ~/Downloads/OverrustleLogs\ Archive/ moobot
```

Personally resulted in:

```bash
$ jq <* '.[] | .dt' | wc -l
1585  # number of comments
 $ jq -r <* '.[] | .channel' | sort -u | wc -l
43  # from these many channels
```

To run tests:

```bash
python3 -m pip install pytest
python3 -m pytest parse.py
```
