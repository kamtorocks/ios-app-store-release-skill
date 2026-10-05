# ios-app-store-release

Claude Code skill:iOS / iPadOS 上架、提审、TestFlight 的实战手册。三层:

1. `SKILL.md` —— 分诊入口 + 11 条防拒规则,触发后自动加载。
2. `references/*.md` —— 实战经验抽象成的通用原则:被拒处理手册、打包上传与版本号、IAP/订阅、Flutter 等跨平台特例、提审清单。
3. `references/official/` —— 苹果官方文档按章节拆分归档(Review Guidelines 分 9 个文件,另有隐私清单、出口合规、账号删除、SIWA、沙盒、ASN、UIScene 等 30+ 篇),可随时联网刷新。

## 安装 / 更新

```bash
git clone git@github.com:kamtorocks/ios-app-store-release-skill.git ~/.claude/skills/ios-app-store-release
git -C ~/.claude/skills/ios-app-store-release pull     # 更新
```

放在 `~/.claude/skills/` 下即为 user scope,所有项目可用。依赖:macOS、`python3`(仅标准库)、Xcode Command Line Tools(`otool`、`codesign`,`inspect_ipa.py` 用)。

## 脚本

```bash
S=~/.claude/skills/ios-app-store-release/scripts
python3 $S/apple_docs.py status                 # 归档新鲜度
python3 $S/apple_docs.py sync --diff            # 联网刷新全部官方文档,打印变更
python3 $S/apple_docs.py guideline 5.1.1(v) 3.1.2(c)   # 精确引用条款原文
python3 $S/apple_docs.py news --days 90         # Apple Developer News(新要求、截止日)
python3 $S/apple_docs.py fetch https://developer.apple.com/documentation/...  # 任意官方页 → Markdown(含 JS 渲染的 DocC 页)
python3 $S/inspect_ipa.py build/ios/ipa/App.ipa # 按审核视角体检 IPA:权限串 ↔ 链接框架双向核对、entitlements、隐私清单、出口合规、UIScene
```

新增归档页:在 `references/official/sources.json` 加一条,`sync <id>`。`INDEX.md` 由 sync 自动生成,勿手改。

## 回写新经验

任何项目解决了新的被拒、ITMS 错误、审核提问或系统升级破坏,都按「审核原话 → 机制 → 修复 → 预防」写进对应 `references/*.md`,只写抽象后的通用原则;项目名、bundle id、产品名、项目路径留在各项目自己的文档里,不进本仓库。然后在本目录 commit + push。提交前确认没有密钥、Team ID、设备 ID。
