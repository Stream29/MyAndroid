# Android 移动端输入法与语音输入

移动端以 Fcitx5 for Android + Rime 为基础，覆盖中文（雾凇拼音）、日语（Kagiroi）、Rime OSS 用户数据同步（RimeSync + RSAF）与语音输入（[DashVoice](../DashVoice/)）。

## 文字输入与 Rime OSS 同步

- 输入法框架：Fcitx5 for Android
  - 中文：Rime 插件 + 雾凇拼音
  - 日语：同一 Rime 实例中的 Kagiroi 方案
  - 英文：Fcitx 英文键盘布局
- Rime 同步目录：`/storage/emulated/0/Android/data/org.fcitx.fcitx5.android/files/data/rime/sync`
- 同步链路：**RimeSync** + **RSAF**（内置 `rclone` 暴露阿里云 OSS Bucket `rime-data` 为 SAF 文档提供者）：
  - 各设备使用独立 `installation_id` 分目录同步 `sync/<installation_id>/`，避免并发写冲突。
  - 移动端手动触发 RimeSync 与 Fcitx Rime 用户数据同步/配置重载。

## 移动端语音输入（DashVoice）

- 源码子模块：[`../DashVoice/`](../DashVoice/)（`git@github.com:Stream29/DashVoice.git`，包名 `io.github.stream29.dashvoice`）。
- 实现栈：Kotlin、Jetpack Compose、Android `RecognitionService`、独立 `InputMethodService`、Room、协程/Flow、`kotlinx.serialization`。
- 识别服务：阿里云百炼 `qwen3-asr-flash-realtime`（API Key 与 Base URL 保存在本地 Room 数据库，不入库）。

## 相关开源组件

| 组件 | 用途 | 源码 |
| --- | --- | --- |
| Fcitx5 for Android | Android 输入法框架 | [fcitx5-android/fcitx5-android](https://github.com/fcitx5-android/fcitx5-android) |
| librime | Rime 输入法引擎 | [rime/librime](https://github.com/rime/librime) |
| 雾凇拼音 | 中文方案和词库 | [iDvel/rime-ice](https://github.com/iDvel/rime-ice) |
| Kagiroi | Rime 日语方案 | [rimeinn/rime-kagiroi](https://github.com/rimeinn/rime-kagiroi) |
| RSAF | Android rclone SAF 提供者 | [chenxiaolong/RSAF](https://github.com/chenxiaolong/RSAF) |
| RimeSync | Android SAF 同步桥 | [zuiwuchang/android-rimesync](https://github.com/zuiwuchang/android-rimesync) |
| DashVoice | Android 端语音输入 | [Stream29/DashVoice](https://github.com/Stream29/DashVoice) |
