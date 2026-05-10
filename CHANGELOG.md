# Changelog

## [0.6.1](https://github.com/Chizukuo/NTE-auto-fish/compare/v0.6.0...v0.6.1) (2026-05-10)


### Bug Fixes

* **build:** embed version.txt in artifacts to resolve 0.0.0 window title ([0904fab](https://github.com/Chizukuo/NTE-auto-fish/commit/0904fab8da946d34921d0390a1112daf6a437c04))

## [0.6.0](https://github.com/Chizukuo/NTE-auto-fish/compare/v0.5.0...v0.6.0) (2026-05-10)


### Features

* add humanization layer with configurable natural variation ([933fc95](https://github.com/Chizukuo/NTE-auto-fish/commit/933fc95ca748de1e3125c36993ef2b5f44cf41ab)), closes [#9](https://github.com/Chizukuo/NTE-auto-fish/issues/9)
* embed admin elevation manifest in GUI exe ([b166e61](https://github.com/Chizukuo/NTE-auto-fish/commit/b166e61ffd189ccda02ea94b2846e6d1732df87c))
* embed version from version.txt in build artifacts and window title ([aab4b82](https://github.com/Chizukuo/NTE-auto-fish/commit/aab4b82f6ec3f081d43d3f0e1b6befddb6994d63))


### Bug Fixes

* apply monitor offset to ROIs for correct multi-monitor coordinates ([cd37599](https://github.com/Chizukuo/NTE-auto-fish/commit/cd37599e832d0169822ed6aa6e8cce895671ba1a)), closes [#13](https://github.com/Chizukuo/NTE-auto-fish/issues/13)
* correct DPG callback arg count for category button ([7821698](https://github.com/Chizukuo/NTE-auto-fish/commit/7821698d31c5a1f3d2e57bd619803ba7e34389b1))
* harden imports, config, logging, and thread safety ([e69fe4e](https://github.com/Chizukuo/NTE-auto-fish/commit/e69fe4e038affce0f9ca1a75b2122593ec613954))
* increase result_wait_secs default from 2.2s to 3.0s ([9b7c30e](https://github.com/Chizukuo/NTE-auto-fish/commit/9b7c30e49c10140f97495650753bf22e636840a1)), closes [#8](https://github.com/Chizukuo/NTE-auto-fish/issues/8)
* make pulse_hold stop-aware and harden sample_reaction ([c6ad421](https://github.com/Chizukuo/NTE-auto-fish/commit/c6ad421b07838b88d116e5a553175039d6dbdd26))
* rename calibration log to avoid false error coloring in GUI ([d4b1861](https://github.com/Chizukuo/NTE-auto-fish/commit/d4b1861e5c4ccb935c700470f1cd46c39ba35e94))

## [0.5.0](https://github.com/Chizukuo/NTE-auto-fish/compare/v0.4.2...v0.5.0) (2026-05-08)


### Features

* add CLI config commands, auto-install deps, and remove template matching from docs ([25eac50](https://github.com/Chizukuo/NTE-auto-fish/commit/25eac508fa4544096b903a8d7f770d17cd5f96b6))
* add responsive UI scaling for different screen resolutions ([53adb79](https://github.com/Chizukuo/NTE-auto-fish/commit/53adb799de5055b87dfb81449ef9ca1935a6a033))


### Bug Fixes

* check error dialog immediately after cast instead of after full animation delay ([ebd5e77](https://github.com/Chizukuo/NTE-auto-fish/commit/ebd5e772486f23f69deb13fef64a1a11f8e586ce))
* **ci:** use PowerShell Compress-Archive instead of zip for CLI packaging ([41ad48b](https://github.com/Chizukuo/NTE-auto-fish/commit/41ad48be98279f96e77ec1e478fd6e8e36d985d7))
* raise error detection brightness threshold to reduce nighttime false positives ([865d1d3](https://github.com/Chizukuo/NTE-auto-fish/commit/865d1d397d570461e2b361d051bbb96366253d6e))
* run error dialog detection in WAITING state to catch no-bait errors ([6b300bc](https://github.com/Chizukuo/NTE-auto-fish/commit/6b300bc98a768637c91929ea7a904b59ba87f570))
* fix multi-monitor calibration for screen capture and ROI detection ([#7](https://github.com/Chizukuo/NTE-auto-fish/pull/7))
* improve default HSV config detection accuracy for sunset and blue-water conditions ([#5](https://github.com/Chizukuo/NTE-auto-fish/pull/5))
