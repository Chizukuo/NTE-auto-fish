# Changelog

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
