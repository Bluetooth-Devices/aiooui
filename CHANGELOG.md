# Changelog

## v0.1.10 (2026-09-25)

### Performance improvements

- Pack the oui table as sorted uint32 keys and search it with bisect (#91) ([`245e55c`](https://github.com/Bluetooth-Devices/aiooui/commit/245e55c15bcd8e7a07ecd9786388bb26eac30d39))
- Memory-map the oui data and binary-search it (−98.5% memory) (#84) ([`6b08609`](https://github.com/Bluetooth-Devices/aiooui/commit/6b086099a40988f154eaca2b24494176ec1151da))

### Bug fixes

- Send a project user agent when downloading the ieee oui list (#87) ([`6de377d`](https://github.com/Bluetooth-Devices/aiooui/commit/6de377d27d43d505002ce94703f067607b9ede3e))
- Update oui data from the ieee registry (#89) ([`60418c0`](https://github.com/Bluetooth-Devices/aiooui/commit/60418c03c570649a772da8e5615515a7d65fa470))

## v0.1.9 (2025-01-19)

### Bug fixes

- Ensure oui data can be loaded in windows (#38) ([`91c29c7`](https://github.com/Bluetooth-Devices/aiooui/commit/91c29c7fdd432c0e2210c41a2d3f114c3b8b022b))

## v0.1.8 (2025-01-18)

### Bug fixes

- Improve retry when oui data is not available during build (#33) ([`087b021`](https://github.com/Bluetooth-Devices/aiooui/commit/087b021de98831abb39d45537c20fcf134651c0a))

## v0.1.7 (2024-10-25)

### Bug fixes

- Include license in project metadata (#23) ([`cf53993`](https://github.com/Bluetooth-Devices/aiooui/commit/cf53993ea2cf8201ab1fee7ca1b79858b6014640))

## v0.1.6 (2024-06-24)

### Bug fixes

- Fix license classifier (#8) ([`ed002d4`](https://github.com/Bluetooth-Devices/aiooui/commit/ed002d4865c39ac7f62d6d550792f9b53fbb57e5))

## v0.1.5 (2024-02-24)

### Bug fixes

- Invalid defaults (#7) ([`5b84d34`](https://github.com/Bluetooth-Devices/aiooui/commit/5b84d3469fee22d4dc821fbd525a362a87c8674e))

## v0.1.4 (2024-02-24)

### Bug fixes

- Build failure (#6) ([`2c0fdc9`](https://github.com/Bluetooth-Devices/aiooui/commit/2c0fdc9685993ffafdb80f5e8a42264748cc792e))

## v0.1.3 (2024-02-24)

### Bug fixes

- Build a none wheel as well (#5) ([`0c4b4ab`](https://github.com/Bluetooth-Devices/aiooui/commit/0c4b4ab1e1872a3e84387bf6cf395339b0a5eaa0))

## v0.1.2 (2024-02-24)

### Bug fixes

- Make failure to update oui data non-fatal (#4) ([`a7bb60d`](https://github.com/Bluetooth-Devices/aiooui/commit/a7bb60deb0980a9bfda3debda499393c89601f50))

## v0.1.1 (2024-02-24)

### Bug fixes

- Raise timeout to get oui data in build (#3) ([`19877f5`](https://github.com/Bluetooth-Devices/aiooui/commit/19877f59395385d602760acb0f1669961bacbaa6))

## v0.1.0 (2024-02-24)

### Features

- First version (#1) ([`667a038`](https://github.com/Bluetooth-Devices/aiooui/commit/667a038e2bdac33cd628044001cb149027bdc75f))

## v0.0.0 (2024-02-24)
