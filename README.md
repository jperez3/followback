# FollowBack

## Description

a tool to help you be petty and see who doesn't follow back on Instagram

## Setup

```bash
python -m pip install uv
uv sync
```

## Usage

The script requires an authenticated Instagram `sessionid` cookie.

```bash
uv run python followback.py <instagram_username> --sessionid <sessionid>
```

or with an environment variable:

```bash
INSTAGRAM_SESSIONID=<sessionid> uv run python followback.py <your_instagram_username>
```

_Hint: In Chrome, go to instagram.com, login, press F12, Go to the Applications tab and copy the `sessionid` value_

Pass `--opposite` to flip it around and see who you follow that *does* follow you back (still filters out business/pro accounts and accounts with 10k+ followers):

```bash
uv run python followback.py <instagram_username> --sessionid <sessionid> --opposite
```




### Disclaimer

* 1000% coded with vibes, use at your own peril.
* Side effects may include:
    - Drama
    - Being sassy
    - Popcorn cravings
