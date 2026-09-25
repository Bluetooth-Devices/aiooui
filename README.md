# aiooui

<p align="center">
  <a href="https://github.com/bluetooth-devices/aiooui/actions/workflows/ci.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/bluetooth-devices/aiooui/ci.yml?branch=main&label=CI&logo=github&style=flat-square" alt="CI Status" >
  </a>
  <a href="https://codecov.io/gh/bluetooth-devices/aiooui">
    <img src="https://img.shields.io/codecov/c/github/bluetooth-devices/aiooui.svg?logo=codecov&logoColor=fff&style=flat-square" alt="Test coverage percentage">
  </a>
  <a href="https://app.codspeed.io/Bluetooth-Devices/aiooui?utm_source=badge"><img src="https://img.shields.io/endpoint?url=https://codspeed.io/badge.json" alt="CodSpeed"/></a>
</p>
<p align="center">
  <a href="https://python-poetry.org/">
    <img src="https://img.shields.io/badge/packaging-poetry-299bd7?style=flat-square&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAASCAYAAABrXO8xAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAJJSURBVHgBfZLPa1NBEMe/s7tNXoxW1KJQKaUHkXhQvHgW6UHQQ09CBS/6V3hKc/AP8CqCrUcpmop3Cx48eDB4yEECjVQrlZb80CRN8t6OM/teagVxYZi38+Yz853dJbzoMV3MM8cJUcLMSUKIE8AzQ2PieZzFxEJOHMOgMQQ+dUgSAckNXhapU/NMhDSWLs1B24A8sO1xrN4NECkcAC9ASkiIJc6k5TRiUDPhnyMMdhKc+Zx19l6SgyeW76BEONY9exVQMzKExGKwwPsCzza7KGSSWRWEQhyEaDXp6ZHEr416ygbiKYOd7TEWvvcQIeusHYMJGhTwF9y7sGnSwaWyFAiyoxzqW0PM/RjghPxF2pWReAowTEXnDh0xgcLs8l2YQmOrj3N7ByiqEoH0cARs4u78WgAVkoEDIDoOi3AkcLOHU60RIg5wC4ZuTC7FaHKQm8Hq1fQuSOBvX/sodmNJSB5geaF5CPIkUeecdMxieoRO5jz9bheL6/tXjrwCyX/UYBUcjCaWHljx1xiX6z9xEjkYAzbGVnB8pvLmyXm9ep+W8CmsSHQQY77Zx1zboxAV0w7ybMhQmfqdmmw3nEp1I0Z+FGO6M8LZdoyZnuzzBdjISicKRnpxzI9fPb+0oYXsNdyi+d3h9bm9MWYHFtPeIZfLwzmFDKy1ai3p+PDls1Llz4yyFpferxjnyjJDSEy9CaCx5m2cJPerq6Xm34eTrZt3PqxYO1XOwDYZrFlH1fWnpU38Y9HRze3lj0vOujZcXKuuXm3jP+s3KbZVra7y2EAAAAAASUVORK5CYII=" alt="Poetry">
  </a>
  <a href="https://github.com/ambv/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square" alt="black">
  </a>
  <a href="https://github.com/pre-commit/pre-commit">
    <img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat-square" alt="pre-commit">
  </a>
</p>
<p align="center">
  <a href="https://pypi.org/project/aiooui/">
    <img src="https://img.shields.io/pypi/v/aiooui.svg?logo=python&logoColor=fff&style=flat-square" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/aiooui.svg?style=flat-square&logo=python&amp;logoColor=fff" alt="Supported Python versions">
  <img src="https://img.shields.io/pypi/l/aiooui.svg?style=flat-square" alt="License">
</p>

---

**Source Code**: <a href="https://github.com/bluetooth-devices/aiooui" target="_blank">https://github.com/bluetooth-devices/aiooui </a>

---

Async OUI lookups

## Installation

Install this via pip (or your favourite package manager):

`pip install aiooui`

## Usage

Start by importing it:

```python
import aiooui

await aiooui.async_load()
aiooui.get_vendor("00:00:00:11:22:33")  # "XEROX CORPORATION"
```

## How lookups work

The OUI table (`src/aiooui/oui.data`, ~40k entries, ~770 KB) is not loaded into a
dict. `async_load()` memory-maps the file read-only in an executor, and
`get_vendor()` binary-searches the key array in place with `bisect`, so the search
itself runs in C. The process keeps almost no private memory for the table
(against ~5.6 MB for a dict). `async_load()` touches every page once, in the
executor, so lookups on the event loop never wait on disk. Those pages are clean,
shared page cache that the kernel can reclaim under memory pressure. If `mmap` is
unavailable, the file is read into `bytes` and searched the same way.

### Data file format

`oui.data` is a small binary table, all integers little-endian `uint32`:

| section | contents                                                     |
| ------- | ------------------------------------------------------------ |
| magic   | `OUI1`                                                       |
| count   | number of entries, `n`                                       |
| keys    | `n` OUIs as 24-bit integers, **sorted ascending, unique**    |
| offsets | `n` byte offsets of each entry's vendor name inside the blob |
| blob    | UTF-8 vendor names, each terminated by `\n`, deduplicated    |

Regenerate it only with `python build_oui.py`, which downloads the IEEE list,
then validates, sorts and packs the entries. The release build runs it before
packaging, so every release ships fresh data. `tests/test_init.py::test_data_file_is_valid` fails if the file is out of
order or malformed. An unsorted key array would make lookups silently return
`None`.

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- prettier-ignore-start -->
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- markdownlint-disable -->
<!-- markdownlint-enable -->
<!-- ALL-CONTRIBUTORS-LIST:END -->
<!-- prettier-ignore-end -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## Credits

This package was created with
[Copier](https://copier.readthedocs.io/) and the
[browniebroke/pypackage-template](https://github.com/browniebroke/pypackage-template)
project template.
