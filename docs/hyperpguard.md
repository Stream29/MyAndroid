# HyperPGuard：K90 Max 与 Note 12 Turbo 配置

这份记录保存 2026-11-18 从 K90 Max 同步到 Note 12 Turbo 的 [HyperPGuard v1.8.9](https://github.com/vivibibi30/hyperpguard/releases/tag/v1.8.9) 配置。它是历史基线，不是新机推荐配置，也不会自动部署。

- [脱敏模板](../templates/hyperpguard/profile-v1.8.9.json)只包含模块包名、公开的目标组件包名和布尔开关。不包含 APK、手机备份、个人应用列表、自定义规则或日志。
- HyperPGuard 是由 LSPosed 加载的 APK，包名 `io.github.vivibibi30.hyperpguard`。该版本[声明](https://github.com/vivibibi30/hyperpguard/blob/v1.8.9/META-INF/xposed/module.prop)最低 API 101、目标 API 102；在 API 101 上能加载，不等于所有功能都可用。

## 已记录状态

| 手机 | 实测环境 | LSPosed 作用域（用户 0） |
| --- | --- | --- |
| REDMI K90 Max（`prague`） | `OS3.0.311.0.WAACNXM` / Android 16；LSPosed 2.2.1 (7912)，API 102 | 17 项：`baseline.scope` 加 `prague_overrides.add_scope` |
| Redmi Note 12 Turbo（`marble`） | `OS3.0.4.0.VMRCNXM` / Android 15；LSPosed 2.0.3 (7716)，API 101 | 16 项：`baseline.scope`；未检测到 `com.miui.packageinstaller`，所以 `g_packageinstaller=false` |

- 规则以 K90 Max 上应用保存的开关为来源；模板的 `baseline.settings_global` 是在 Note 12 Turbo 上实际写入、读回的 49 项布尔配置，**不是** K90 Max 的运行时设置导出。未列出的键沿用 [v1.8.9 的默认值](https://github.com/vivibibi30/hyperpguard/blob/v1.8.9/src/io/github/vivibibi30/hyperpguard/Config.java)。
- 作用域和应用启用状态是两回事。同步时备用机的 16 个目标中，4 个在系统里启用，12 个已禁用；没有为同步重新启用任何系统组件。
- 备用机已验证小米应用商店能冷启动，模块成功注入并读取 49 项配置。未观察到具体上报拦截命中；安全中心、可信服务、推送等不在本次功能验证范围。

## 恢复与回退

1. **先确认设备和版本，再备份。** 用 `adb devices -l` 与 `adb -s "$serial" shell getprop ro.product.device` 核对目标，确认 Android 用户和 LSPosed API。记下 HyperPGuard 原来的启用状态、作用域和 `adb -s "$serial" shell settings get global hyperpguard_conf` 的值（包括原键不存在的情况）。备份只保存在本地，不提交。
2. **先停用规则，再核对作用域。** 安装官方同版 APK；恢复配置时先让 `master=false`，在 LSPosed 中只选择模板里目标机上仍存在的包。`marble` 用基线；`prague` 额外加入 `com.miui.packageinstaller` 并应用对应的开关覆盖。若目标包已禁用，不要为了恢复作用域而启用它。不要先打开 HyperPGuard 应用或同意批量作用域请求：初次启动遇到空作用域时，应用会请求添加所有候选目标。
3. **写入并读回规则。** 模板不是可直接导入的 LSPosed 备份。模块在 `Settings.Global` 的 `hyperpguard_conf` 下读取 `键=布尔值`，用 `|` 分隔；`g_*` 也需要与实际 LSPosed 作用域对应。先核对序列化结果和影响范围，再用选定设备的 ADB 写入该键，读回比对。作用域核对无误后，才将 `master` 恢复为模板值。不要编辑 LSPosed 数据库或覆盖其他模块。
4. **只验证一个目标。** 先冷启动小米应用商店，确认模块日志出现 `attach market` 和 `config loaded`。前者表示已注入，后者表示已读配置；只有对应的 `X(...)` 日志才表示某条网络规则实际命中。不要批量重启系统组件。
5. **有异常就回退。** 在 LSPosed 仅停用 HyperPGuard，恢复此前的 `hyperpguard_conf`；原键不存在则删除该键。恢复原作用域和启用状态，必要时只重启受影响的应用；不需要卸载 APK。

在 MyAndroid 根目录可离线预览任一机型的序列化配置（不会操作手机）：

```sh
device=marble  # 或 prague
jq -r --arg device "$device" '
  if $device == "marble" then .baseline.settings_global
  elif $device == "prague" then .baseline.settings_global + .prague_overrides.settings_global
  else error("unknown device") end
  | to_entries | sort_by(.key) | map("\(.key)=\(.value)") | join("|")
' templates/hyperpguard/profile-v1.8.9.json
```

**恢复前重点复核：**这个快照不是「只拦应用商店统计」。它还启用了可能影响 ADB 安装授权、紧急定位以及查找设备的规则（参见上游[安全中心](https://github.com/vivibibi30/hyperpguard/blob/v1.8.9/src/io/github/vivibibi30/hyperpguard/MainActivity.java#L124-L140)及[可信服务](https://github.com/vivibibi30/hyperpguard/blob/v1.8.9/src/io/github/vivibibi30/hyperpguard/MainActivity.java#L215-L218)开关说明）。没有明确需求时，不要在其他机器上全量照搬。
