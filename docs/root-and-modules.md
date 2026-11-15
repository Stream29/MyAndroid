# Android Root, Modules & Proxy Setup

本指南记录当前设备（Xiaomi 15 / `prague`，Xiaomi HyperOS 2 / Android 15）验证可行的 Root 架构、Magisk/KernelSU 模块组合、Xposed 插件、Play Integrity 穿透方案以及代理与网络配置。便于后续迁移新设备时快速还原。

---

## 1. Root 架构方案

- **Root 核心**：**KernelSU**（KernelSU Next / 官方 KernelSU）
  - 采用 GKI / 内核级 Hook，比传统 Magisk 更隐蔽，对系统 system 分区零修改。
  - 管理器应用：`me.weishu.kernelsu`。
- **Zygisk 支持**：**Zygisk Next** (`zygisksu`)
  - 模块：Standalone implementation of Zygisk for KernelSU。
- **挂载增强**：**Hybrid Mount** (`hybrid_mount`)
  - KernelSU / APatch 的 Mount 编排元模块（Metamodule）。
- **救砖防护**：**音量键极速救砖** (`RescueBrick`)
  - 开机动画阶段三击音量+进入安全模式禁用所有模块；三击音量-禁用 Xposed 模块。新机折腾必备。

---

## 2. 核心模块清单 (`/data/adb/modules`)

| 模块 ID | 模块名称 | 用途 / 说明 |
| --- | --- | --- |
| `zygisksu` | **Zygisk Next** | 在 KernelSU 下提供 Zygisk API 支持 |
| `hybrid_mount` | **Hybrid Mount** | 解决 OverlayFS / 模块挂载冲突与元模块调度 |
| `RescueBrick` | **音量键极速救砖** | 启动异常时通过物理按键安全停用模块 |
| `zygisk_lsposed` | **LSPosed (Zygisk 版)** | Xposed 框架运行环境 (v2.1.1+) |
| `playintegrityfix` | **Play Integrity Fix** | 修复 Google Play Integrity (MEETS_DEVICE_INTEGRITY) |
| `tricky_store` | **TEESimulator-RS / TrickyStore** | 软件模拟硬件级密钥证明 (Key Attestation)，突破 Strong 验证拦截 |
| `hma_oss_zygisk` | **HMA-OSS Zygisk** | 隐藏应用列表 (Hide My Applist) 的 Zygisk 后端 |
| `WorkSettingPro` | **爱玩机工具箱 (核心拓展)** | 免挂载 system 辅助调整系统高级设置 |

---

## 3. Play Integrity & 软硬件证明配置

- **PIF 参数 (`/data/adb/pif.prop`)**：
  - 模拟 Pixel 7 / Panther 等受支持指纹，绕过基础与设备级完整性校验。
- **Tricky Store (`/data/adb/tricky_store`)**：
  - `keybox.xml`：有效的 Keybox 证书文件（请自行妥善私密保存，不可提交进公开 Git 仓库）。
  - `target.txt`：配置需要伪造 Key Attestation 的目标应用包名清单（如 Google Play 服务 `com.google.android.gms!`、银行类 App 等）。

---

## 4. Xposed 增强插件 (LSPosed)

- **HyperCeiler (`com.sevtinge.hyperceiler`)**：
  - 核心功能：MIUI / HyperOS 系统全面增强、广告拦截、云控禁用、通知与控制中心优化、系统更新弹窗屏蔽。
- **Hide Mock Location (`io.github.auag0.hidemocklocation`)**：
  - 模拟位置检测隐藏。
- **HMA-OSS (`org.frknkrc44.hma_oss`)**：
  - 配合 Zygisk 模块隐藏 Root 应用、管理器及特定插件列表，防止银行等检测软件扫描安装包。

---

## 5. 代理与网络客户端

- **Clash / Mihomo 客户端**：
  - **Clash Verge / Clash Nyanpasu 同源移动端** 或 **Clash Meta for Android (`com.follow.clash`)** / **Bettbox (`com.appshub.bettbox`)**。
  - 配合主仓 `mihomo/` 中的配置规则，支持 Fake-IP、分流以及直连规则。
- **移动端 Rime 同步与网络存储**：
  - **RSAF (`com.chiller3.rsaf`)**：通过内置 rclone 连接阿里云 OSS Bucket `rime-data`。
  - **RimeSync (`com.king011.android.rimesync`)**：连接 SAF 存储与 Fcitx5 for Android 词库目录。

---

## 6. 新机落地与迁移检查清单 (SOP)

1. **解 BL 锁并刷入 KernelSU 支持内核**（或使用 GKI boot 镜像刷入 KernelSU）。
2. **安装 KernelSU App**，授予 Root 权限并安装救砖模块 `RescueBrick`。
3. **依次刷入核心基础模块**：
   - `hybrid_mount` -> 重启
   - `zygisksu` (Zygisk Next) -> 重启
   - `zygisk_lsposed` -> 重启
4. **配置安全与防检**：
   - 刷入 `playintegrityfix` 与 `tricky_store`，将私有 `keybox.xml` 放入 `/data/adb/tricky_store/` 并配置 `target.txt`。
   - 刷入 `hma_oss_zygisk` 并安装 HMA-OSS App 配置白名单模板。
5. **系统调优与隐私加固**：
   - 安装 `HyperCeiler` 并在 LSPosed 中启用目标作用域。
   - 执行 [`../bin/hyperos-privacy`](../bin/hyperos-privacy) 运行自动化隐私与云控加固：
     ```bash
     ./bin/hyperos-privacy check
     ./bin/hyperos-privacy apply
     ```
6. **网络与输入法恢复**：
   - 安装 Clash / Bettbox 导入节点。
   - 参照 [`docs/ime.md`](ime.md) 部署 Fcitx5 for Android、RSAF、RimeSync 及 DashVoice。
