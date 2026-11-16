# Android Root, Modules & Play Integrity Setup

本指南记录已验证可行的 KernelSU Root 架构、Zygisk/LSPosed 模块组合、Play Integrity（`PIF` + `TEESimulator-RS`）伪装与证书配置、代理网络方案，以及**遇到“三红 / `UNEVALUATED`”时的独立排查与恢复流程**。

> **安全边界**：本公开指南与 [`../templates/play-integrity/`](../templates/play-integrity/) 仅保留通用模板与脱敏说明；真实的 `keybox.xml`、`hbk`、`boot_hash.bin`、`boot_key.bin` 以及包含个人已装包名列表的 `target.txt` / `hma-config.json` 必须保存在本地受 Git 忽略的目录（例如协调仓库中的 `secret/`，`0700`/`0600` 权限），严禁提交进 Git。

---

## 1. 已验证设备基线与 Root 架构

| 设备定位 | 型号与代号 | 系统 / Android 版本 | 已验证完整性等级 | 说明 |
| --- | --- | --- | --- | --- |
| 主力机 | **REDMI K90 Max** (`2604FRK1EC` / `prague`) | HyperOS 3 (`OS3.0.311.0.WAACNXM`) / Android 16 (SDK 36) | **三绿全过** (`BASIC` + `DEVICE` + `STRONG`) | 使用 `TEESimulator-RS` + `PlayIntegrityFix [INJECT]` + 有效 ECDSA Keybox |
| 备用机 | **Redmi Note 12 Turbo** (`23049RAD8C` / `marble`) | HyperOS / Android 15 (SDK 35) | **通过 `MEETS_DEVICE_INTEGRITY`** | 同套 `TEESimulator-RS` + `PIF` + `hbk` + Keybox + 新版 Play Store (`50.2.x`)；叠加 `TA_utl` 对齐 Boot 属性 |

- **Root 核心**：**KernelSU**（`v3.2.4` / `v3.2.5+`，管理器 `me.weishu.kernelsu`）
  - GKI 内核级 Hook，不改动 `system` 分区。
- **挂载元模块**：**Hybrid Mount**（`hybrid_mount` `v6.2.6+`）
  - KernelSU / APatch 的 OverlayFS / Magic Mount / VFS 编排元模块（Metamodule）。
- **Zygisk 实现**：**Zygisk Next**（`zygisksu` `v1.5.2 (864)+`）
  - 为 KernelSU 提供独立 Zygisk 注入环境；GMS 重大更新后需保持版本同步。
- **救砖防护**：**音量键极速救砖**（`RescueBrick` `22.6`）
  - 开机动画阶段三击音量+进入安全模式禁用全部模块；三击音量-禁用 Xposed 模块。

---

## 2. 核心模块清单 (`/data/adb/modules`)

| 模块 ID | 模块名称 / 推荐分支 | 已验证版本 | 用途与关键注意 |
| --- | --- | --- | --- |
| `hybrid_mount` | **Hybrid Mount** | `v6.2.6` | KernelSU 元模块（`metamodule=1`） |
| `zygisksu` | **Zygisk Next** | `v1.5.2 (864)` | Zygisk 运行时（`LSPosed/ZygiskNext`） |
| `zygisk_lsposed` | **LSPosed (Zygisk 版)** | `v2.2.1 (7912)`（Manager `2.1.1`） | Xposed 框架运行环境（支持 Android 9–17） |
| `playintegrityfix` | **Play Integrity Fix [INJECT]**（`KOWX712/PlayIntegrityFix` `inject_s` 分支） | `v4.9-inject-s` | 指纹注入与 Build/Props/Vending 伪装（旧版 `v4.5` 在新版 GMS 下易失效） |
| `tricky_store` | **TEESimulator-RS**（`Enginex0/TEESimulator-RS`） | `v6.0.1-307` | **关键**：native `supervisor` + `libTEESimulator.so` + `libcertgen.so` 模拟硬件 Key Attestation。**旧版 `5ec1cff/TrickyStore v1.4.1`（`service.apk` Java Hook）在 GMS `26.44.32+` 下会失效并返回全 `UNEVALUATED`** |
| `hma_oss_zygisk` | **HMA-OSS Zygisk** | `zygisk-9f788419` | Hide My Applist 的 Zygisk 后端 |
| `WorkSettingPro` | **爱玩机工具箱（核心拓展）** | `19.02` | 免挂载系统辅助调整 |
| `RescueBrick` | **音量键极速救砖** | `22.6` | 物理按键安全停用模块 |
| `TA_utl` *(按需)* | **Bootloader/Prop 对齐辅助** | — | 在 `marble` 等机型上通过 `prop.sh` 补齐 `ro.boot.verifiedbootstate=green`、`ro.boot.flash.locked=1`、`ro.boot.vbmeta.device_state=locked` 等属性 |

---

## 3. Play Integrity & 伪装配置详解

Play Integrity 能否通过，同时依赖 **PIF 指纹/属性注入**、**安全补丁四端一致** 与 **TEESimulator-RS 证书链** 三条链路：

### 3.1 PIF 参数 (`/data/adb/pif.prop`)

- 模板参考：[`../templates/play-integrity/pif.prop.example`](../templates/play-integrity/pif.prop.example)
- **路径优先级**：`autopif.sh` 会写入 `/data/adb/pif.prop`，且运行时 **`/data/adb/pif.prop` 优先于 `/data/adb/modules/playintegrityfix/pif.prop`**；不要只改模块目录里的旧文件而忽略 `/data/adb/pif.prop`。
- **必开开关**：
  - `spoofBuild=true`
  - `spoofProps=true` —— **关键坑点**：`autopif.sh` 会继承原 `pif.prop` 的布尔开关；若原文件为 `spoofProps=false`，刷新指纹后仍会全红 `UNEVALUATED`。
  - `spoofVendingBuild=true`
  - 一般保持关闭：`spoofProvider=false`、`spoofSignature=false`、`spoofVendingSdk=false`、`DEBUG=false`。
- **指纹来源**：执行 `/data/adb/modules/playintegrityfix/autopif.sh` 从官方 Pixel Canary/Beta 抓取最新 `FINGERPRINT`、`MODEL`、`SECURITY_PATCH` 与 `DEVICE_INITIAL_SDK_INT`。

### 3.2 安全补丁联动一致（四处必须对齐）

当 `pif.prop` 中的 `SECURITY_PATCH`（如 `2026-11-05`）与系统不一致时，Play Integrity 会直接返回 `UNEVALUATED` 或 `FAIL`。四处状态必须保持一致：

1. `/data/adb/pif.prop` 中的 `SECURITY_PATCH=YYYY-MM-DD`
2. `/data/adb/tricky_store/pif_auto_security_patch`（**空标记文件**：存在时 `autopif.sh` 才会自动调用 `security_patch.sh`）
3. `/data/adb/tricky_store/security_patch.txt`（格式见 [`../templates/play-integrity/security_patch.txt.example`](../templates/play-integrity/security_patch.txt.example)）：
   ```ini
   system=YYYYMM
   boot=YYYY-MM-DD
   vendor=YYYY-MM-DD
   ```
4. `/data/adb/modules/playintegrityfix/system.prop` 及实时系统属性 `ro.build.version.security_patch` / `ro.vendor.build.security_patch`（均为 `YYYY-MM-DD`）。

### 3.3 TEESimulator-RS 目录 (`/data/adb/tricky_store`)

- **`keybox.xml`**：有效的 ECDSA 证书链（`0644`）；仅在私有加密/忽略目录保存，不可提交公开仓库。
- **`hbk`（32 字节）**：与 `TEESimulator-RS` 配套的密钥派生/校验文件；多机迁移 `keybox.xml` 时建议一并同步。
- **`boot_hash.bin` / `boot_key.bin`**：守护进程读取/生成的 32 字节校验文件，正常由 `TEESimulator-RS` 自动维护。
- **`tee_status`**：`teeBroken=false` 表示可正常模拟。
- **`target.txt`**：需要伪造 Key Attestation 的包名清单，基准模板见 [`../templates/play-integrity/target.txt.baseline`](../templates/play-integrity/target.txt.baseline)：
  - **必须加 `!` 后缀**（强制证书生成模式）：`com.google.android.gms!`、`com.android.vending!`、`com.google.android.gsf!`、`gr.nikolasspyr.integritycheck!`。
  - **普通防检测 App**（银行、钱包、PayPal、海外工具等）：按包名写入，不加 `!`。
- **密钥缓存目录**：
  - `TEESimulator-RS` 使用 `/data/adb/tricky_store/persistent_keys/`（其 `action.sh` 音量键操作清理的就是该目录）。
  - 旧版 TrickyStore 残留目录为 `/data/adb/tricky_store/key_db/`。更换 Keybox 或修改 `target.txt` 后，两处都应清空。

### 3.4 Bootloader / Prop 对齐（`TA_utl` 与 `PIF` 服务脚本）

- `PlayIntegrityFix` 在 `post-fs-data.sh` 与 `service.sh` 中自动将 `ro.boot.verifiedbootstate=green`、`ro.boot.flash.locked=1`、`ro.boot.vbmeta.device_state=locked`、`ro.boot.veritymode=enforcing`、`ro.build.type=user`、`ro.build.tags=release-keys`、`ro.debuggable=0`、`ro.adb.secure=1` 等属性 `resetprop` 回官方锁定态。
- 如 `marble` 等机型还装有 `TA_utl`，其 `prop.sh` 会补充检查并重置这些属性，并读取 `/data/adb/boot_hash`（如有）对齐 Verified Boot Hash；迁移时勿将 `TA_utl` 与同功能自写 prop 模块重复叠加导致冲突。

---

## 4. 独立排查与恢复 SOP（下次遇到“三红”怎么自己修）

已沉淀一键脚本 [`../bin/play-integrity`](../bin/play-integrity)（ADB + Root）。连接手机后优先执行只读自检，按 `[FAIL]` 项对应处理即可。

### 4.1 一键工具用法

```bash
# 1. 只读诊断：检查模块架构、守护进程、PIF开关、四端补丁一致、Keybox有效期、target.txt(!)
./bin/play-integrity check

# 2. 刷新 Pixel Canary 指纹 + 强制开启 spoofProps=true + 对齐安全补丁 + 重启 GMS/Play
./bin/play-integrity sync-pif

# 3. 校验并部署新的 keybox.xml（自动备份旧文件、同步同目录 hbk、清缓存并重启守护进程）
./bin/play-integrity deploy-keybox --keybox /path/to/keybox.xml

# 4. 补全 target.txt 核心 Google 包名的 `!` 后缀（保留原有 App 列表）
./bin/play-integrity ensure-targets

# 5. 清缓存并重启 TEESimulator-RS 与 GMS/Play Store
./bin/play-integrity restart

# 6. 从已调通机器备份密钥、伪装及 Root 配置到本地 0700/0600 忽略目录
# （含 keybox、hbk、pif.prop、security_patch、target.txt、HMA、LSPosed、HyperCeiler、KSU 授权表，默认写入 ../../secret/android/<device>/）
./bin/play-integrity backup
```

### 4.2 手动分步排障矩阵（脱离电脑或在手机端直接操作）

1. **先区分是 `UNEVALUATED` 还是 `FAIL`**：
   - 在 **Play Integrity API Checker** 点击右上角 `<>` 看 Raw JSON：
     - 若 `appRecognitionVerdict` / `deviceActivityLevel` / `appLicensingVerdict` 全为 **`UNEVALUATED`**：说明代理链路不通 Google Play Integrity 后端、Play 商店版本过旧，或本地 PIF / TEESimulator-RS / 补丁未正确挂载。
     - 若返回 `PLAY_RECOGNIZED` 但 `deviceRecognitionVerdict` 缺少绿项（或为空）：说明请求已到达 Google，但 **Keybox 被吊销/过期** 或 **模块版本/属性未能通过服务器当前策略**。
2. **检查模块架构与进程（GMS `26.44+` 最常见坑）**：
   - 在 KernelSU 确认已安装且启用：`Hybrid Mount` + `Zygisk Next` + `Play Integrity Fix [INJECT]` + **`TEESimulator-RS`**。
   - 若 `tricky_store` 模块仍是旧版 `service.apk`（如 `5ec1cff v1.4.1`），直接替换为 `TEESimulator-RS` 并重启手机；用 `su -c 'ps -ef | grep -E "supervisor|TEESimulator"'` 确认守护进程在线，用 `tail -n 20 /data/adb/tricky_store/logs/certgen.log` 确认出现 `assembled native cert result`。
3. **验证 Keybox 本地证书链未过期**：
   - 替换前用电脑检查 PEM 证书时间（`openssl x509 -noout -dates -subject`），或直接用 `./bin/play-integrity deploy-keybox` 自动校验；部署后必须清理 `persistent_keys/*` 与 `key_db/*`，重启 `supervisor` 并强停 `com.google.android.gms`、`com.google.android.gms.unstable`、`com.android.vending`。
4. **刷新 PIF 与对齐安全补丁**：
   - 在 KernelSU 中点击 `Play Integrity Fix` 的 **Action**（或运行 `sh /data/adb/modules/playintegrityfix/autopif.sh`）。
   - 检查 `/data/adb/pif.prop` 确认 `spoofBuild=true`、`spoofProps=true`、`spoofVendingBuild=true`。
   - 确认存在 `/data/adb/tricky_store/pif_auto_security_patch`，并执行 `sh /data/adb/modules/playintegrityfix/security_patch.sh` 同步 `security_patch.txt` 与 `system.prop`。
5. **核对 Play Store 与网络出口**：
   - 检查 `com.android.vending` 版本（旧版本如 `36.x` 可能导致验证异常，更新至当前稳定版如 `50.2.x`）。
   - 确认代理客户端已开启全局/TUN 并正常连通 Google 服务。
6. **识别机型预期上限**：
   - Android 16 / SDK 36（如 `prague`）在配置正确时可同时拿到 `BASIC` + `DEVICE` + `STRONG` 三绿。
   - Android 15 / SDK 35 老平台（如 `marble`）在部分 Google 新策略下可能仅下发 **`MEETS_DEVICE_INTEGRITY`**（一绿）；只要 `deviceRecognitionVerdict` 含 `MEETS_DEVICE_INTEGRITY`，即可满足绝大多数 Google 服务与 Play 保护认证需求。

---

## 5. Xposed 增强插件与特定应用适配

### 5.1 LSPosed 模块

- **HyperCeiler (`com.sevtinge.hyperceiler`)**：
  - MIUI / HyperOS 系统增强、广告与云控禁用、通知与控制中心优化、系统更新弹窗屏蔽。
- **Hide Mock Location (`io.github.auag0.hidemocklocation`)**：
  - 模拟位置检测隐藏。
- **HMA-OSS (`org.frknkrc44.hma_oss`)**：
  - 配合 `hma_oss_zygisk`，按 `'hide root'`（隐藏 KernelSU / LSPosed / HMA / 检测工具等）与 `'hide sensitive'`（隐藏代理/社交/敏感工具）两套黑名单模板对金融、政务、国产商业及高风控海外应用（如排查 `com.paypal.android.p2pmobile` 时可纳入作用域）隔离包列表。
  - [`../bin/hyperos-privacy`](../bin/hyperos-privacy) 仅内置通用最小基线；完整个人包名策略模板参考 [`../templates/hyperos-privacy/hma-policy.example.json`](../templates/hyperos-privacy/hma-policy.example.json)，可通过 `--hma-config` 指定或置于协调仓本地 `secret/android/hma-policy.json` 自动加载。

### 5.2 国行 GMS 权限与个别 App 闪退备忘

- **国行 HyperOS 读取 SIM 号码被拒**：
  - Google 账号验证读取不到本机号码时，检查并放行 GMS `appops`：
    ```bash
    adb shell appops set com.google.android.gms READ_PHONE_NUMBERS allow
    adb shell appops set com.google.android.gms USE_ICC_AUTH_WITH_DEVICE_IDENTIFIER allow
    ```
  - 注意：纯流量 eSIM（未写入 `EF_MSISDN`、基带不支持短信）无法靠权限/模块变出上行短信能力。
- **PayPal (`com.paypal.android.p2pmobile` 10.20.1) 在 Android 16 / HyperOS 启动闪退（临时绕过，存在副作用）**：
  - 崩溃日志与 `AppVerifier` 字节码分析表明：启动时由 `androidx.startup.InitializationProvider` 拉起 `AppVerifierInitializer` -> `AppVerifier.run()`，在运行环境/完整性检测失败后故意触发自毁异常（如 `ArrayIndexOutOfBoundsException: index=-1` 或 `OutOfMemoryError`）。注意先排查是否已将 `com.paypal.android.p2pmobile` 纳入 HMA-OSS 与 `target.txt`。
  - 临时绕过命令（**注意副作用**：`androidx.startup.InitializationProvider` 同时挂载约 30 个初始化器，含 `MagnesInitializer` 设备风控、`ClientTokenInitializer` 等，禁用后虽可进入登录页，但登录与绑卡阶段是否触发风控尚未验证；App 升级后也可能变化）：
    ```bash
    adb shell su -c "pm disable com.paypal.android.p2pmobile/androidx.startup.InitializationProvider"
    # 如需恢复原状测试 HMA-OSS / LSPosed 针对性 Hook 方案：
    adb shell su -c "pm enable com.paypal.android.p2pmobile/androidx.startup.InitializationProvider"
    ```

---

## 6. 代理与网络客户端

- **Clash / Mihomo 客户端**：
  - **Clash Meta for Android (`com.follow.clash`)** / **Bettbox (`com.appshub.bettbox`)**，配合主仓 `mihomo/` 配置启用 TUN 与 Fake-IP，确保 `IPv4`/DNS 经 `tun0`、未泄漏原生 `IPv6`。
- **移动端 Rime 同步与网络存储**：
  - **RSAF (`com.chiller3.rsaf`)**：通过内置 rclone 连接阿里云 OSS Bucket `rime-data`。
  - **RimeSync (`com.king011.android.rimesync`)**：连接 SAF 存储与 Fcitx5 for Android 词库目录。

---

## 7. 新机落地与迁移检查清单 (SOP)

1. **解 BL 锁并刷入 KernelSU 支持内核**（或使用 GKI boot 镜像刷入 KernelSU）。
2. **安装 KernelSU App**，授予 Root 权限并安装救砖模块 `RescueBrick`。
3. **依次刷入核心基础模块**：
   - `hybrid_mount` -> 重启
   - `zygisksu` (Zygisk Next `v1.5.2+`) -> 重启
   - `zygisk_lsposed` (`v2.2.1+`) -> 重启
4. **部署 Play Integrity 与软硬件证明**：
   - 刷入 `KOWX712/PlayIntegrityFix`（`v4.9-inject-s+`）与 `Enginex0/TEESimulator-RS`（`v6.0.1-307+`，勿用旧版 `service.apk`），重启一次。
   - 使用 [`../bin/play-integrity`](../bin/play-integrity) 完成部署与核验：
     ```bash
     ./bin/play-integrity deploy-keybox --keybox /path/to/secret/keybox/keybox.xml
     ./bin/play-integrity sync-pif
     ./bin/play-integrity ensure-targets
     ./bin/play-integrity check
     ```
   - 刷入 `hma_oss_zygisk` 并导入本地 HMA-OSS 配置模板。
5. **系统调优与隐私加固**：
   - 安装 `HyperCeiler` 并在 LSPosed 中启用目标作用域。
   - 执行 [`../bin/hyperos-privacy`](../bin/hyperos-privacy) 运行自动化隐私与云控加固：
     ```bash
     ./bin/hyperos-privacy check
     ./bin/hyperos-privacy apply
     ```
6. **网络与输入法恢复**：
   - 安装 FlClash / Bettbox 导入节点。
   - 参照 [`docs/ime.md`](ime.md) 部署 Fcitx5 for Android、RSAF、RimeSync 及 DashVoice。
