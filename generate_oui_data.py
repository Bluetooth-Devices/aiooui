"""Build oui table."""

import pathlib

import requests  # type: ignore


def generate() -> None:
    """Generate the OUI data."""
    resp = requests.get("http://standards-oui.ieee.org/oui.txt", timeout=10)
    resp.raise_for_status()
    oui_bytes = resp.content
    oui_to_vendor = {}
    for line in oui_bytes.splitlines():
        if b"(base 16)" in line:
            oui, _, vendor = line.partition(b"(base 16)")
            oui_to_vendor[oui.strip()] = vendor.strip()
    file = pathlib.Path(__file__)
    target_file = file.parent.joinpath("src").joinpath("aiooui").joinpath("oui.data")
    with open(target_file, "wb") as f:
        f.write(b"\n".join(b"=".join((o, v)) for o, v in oui_to_vendor.items()))


if __name__ == "__main__":
    generate()
