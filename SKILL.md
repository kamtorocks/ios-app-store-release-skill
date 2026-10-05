---
name: ios-app-store-release
description: "Field guide for shipping iOS/iPadOS apps through App Review and TestFlight: rejections by guideline (2.1 demo video/incomplete, 2.1(b) IAP, 3.1.2 subscriptions, 4.0/4.8 Sign in with Apple, 5.1.1 privacy/permissions/account deletion, 5.1.2 third-party AI), ITMS-xxxxx upload errors, version/build numbers, altool/API-key upload, flavors, purpose strings, privacy manifests, export compliance, StoreKit sandbox and server verification, metadata and screenshots, and new-iOS launch breakages (iOS 27 UIScene). Bundles Apple official docs archived by section, plus scripts to fetch live Apple docs (incl. JS-only DocC pages), quote any guideline clause, read Apple Developer News, and inspect a built IPA as review sees it. Use whenever someone prepares, submits, uploads or debugs an iOS release or pastes a rejection or App Store Connect email, in any stack (native, Flutter, React Native, Expo, Capacitor). Triggers: 提审, 上架, 被拒, 审核, TestFlight, 打包上传, 内测, 订阅审核, 隐私清单."
---

# iOS App Store Release

Field-tested release lessons, abstracted into principles that apply to any app and any stack. Apple's own documents are archived under `references/official/`, and the scripts query the live site.

`$SKILL` below means this skill's base directory (shown when it loads; normally `~/.claude/skills/ios-app-store-release`).

## 1. Establish ground truth first

Apple changes the rules several times a year: guideline revisions, SDK and Xcode minimums every spring, privacy-manifest and age-rating requirements. Treat your own memory as stale, the archive as a dated cache, and the live site as the authority.

- At the start of a release task, run `python3 $SKILL/scripts/apple_docs.py status`. If anything is STALE, or the question involves a deadline, minimum version or recent change, run `sync` (add `--diff` to see what changed) and `news --days 120`.
- Before citing a guideline, read it: `apple_docs.py guideline 2.1(b) 5.1.1(v)`. Quote the operative sentence. Clause letters move, so never cite a number from memory.
- For developer.apple.com/documentation or Human Interface Guidelines URLs, use `apple_docs.py fetch <url>`. These pages are JavaScript apps, so a generic web fetch returns an empty shell.
- Search the archive with grep, for example `grep -rn "revoke" $SKILL/references/official/`. `references/official/INDEX.md` maps each file to its topic.
- For an error code or rejection wording that the official docs don't cover, web-search the exact string (Apple Developer Forums first) and label the result as community evidence, not policy.
- If `sync` reports a CHANGED source, read its diff. If a rule in `references/*.md` is now wrong, fix that file in the same session.

## 2. Route by situation

| Situation | Read |
| --- | --- |
| Rejection message, "Guideline x.y" email, App Review question | references/rejection-playbook.md |
| Preparing a submission (first release or update) | references/submission-checklist.md |
| Signing, version/build numbers, upload, ITMS codes, TestFlight, flavors | references/build-and-upload.md |
| App broken only on a new iOS; reading device evidence | references/build-and-upload.md, sections "New iOS releases" and "Device evidence" |
| IAP or subscriptions: products missing, reviewer can't buy, paywall rules, server verification | references/iap-subscriptions.md |
| Flutter specifics (also Capacitor/native-Swift notes) | references/flutter-ios.md |
| React Native / Expo specifics (EAS, config plugins, OTA) | references/react-native-expo.md |
| What Apple's documentation literally says | references/official/ (via INDEX.md, grep, or the `guideline` command) |

## 3. Rules that prevent most rejections

1. Review judges the binary, not your intentions. Linked frameworks, purpose strings, entitlements and reachable UI all show capability. A feature hidden behind a flag still exists if its framework is linked or its permission string is declared. Inspect the artifact you upload (`scripts/inspect_ipa.py`), not the source tree.
2. Keep capabilities symmetric. Each purpose string needs a feature reachable in that build, and each linked protected API needs a purpose string (otherwise ITMS-90683). The only reliable way to ship without a feature is to compile it out: conditional dependency plus a stub.
3. Everything the reviewer can reach must work end to end with the demo account and the production backend: no dead buttons, hidden gestures, waiting splash screens, or silent purchase failures. If something configured can't be reviewed, say why in Review Notes.
4. Disclose, then ask. Personal data leaving the device for any third party, AI providers included, needs in-app disclosure and explicit consent before the first send. Permission prompts appear in context, after an optional single-button pre-screen labelled "Continue" or "Next", and never at launch.
5. Sign in with Apple supplies name and email only once: persist them on first authorization and never ask again. Use Apple's own button, and revoke tokens when the account is deleted.
6. Subscriptions: the billed amount is the most prominent price, intro offers are secondary but always shown, there are no fake deadlines, and the purchase flow has working Terms and Privacy links plus Restore.
7. App Review buys in the sandbox against your production backend. The server must accept sandbox transactions, tolerate expired re-deliveries, and grant access when entitlements are read rather than rejecting at verify time.
8. Build numbers are managed by the export. Set only the marketing version. A manually injected large build number permanently anchors that version's build line.
9. Release builds come from a script on a clean tree, with every flag explicit. Dev flags leak through generated files, and flavor scripts that edit tracked files leave state that gets committed by accident. Internal builds use a separate bundle ID, or are exported as TestFlight Internal Only.
10. Each new major iOS can break the live app with no change on your side (iOS 27: no UIScene adoption means a trap at launch). Install the shipping build on every iOS beta from June, and submit fixes before the September release.
11. A crash report is the only conclusive device evidence. Debugger-less debug launches, devicectl exit codes and suspended background apps all produce misleading signals.

## 4. Responding to a rejection

Produce these, in order:
1. The guideline text (via `guideline`) next to the reviewer's exact words.
2. The mechanism: what in the binary, metadata or backend showed the reviewer the problem.
3. The fix class: metadata only, server only (reply in App Store Connect, same build), or new binary. Prefer the fix that removes the cause, not one that hides the symptom; every half-measure costs a review round.
4. A reply draft in English for App Store Connect: what changed, where to see it, demo credentials and steps. Factual and short. Appeal only when a compliant app was misread.
5. Prevention: the checklist line or build guard that would have caught it. Once the fix is confirmed, add any new lesson to this skill (section 6).

Talk to the user in their own language. Write App Review replies in English.

## 5. Scripts

- `scripts/apple_docs.py` (stdlib Python):
  - `fetch URL [-o file]` converts any Apple page to Markdown.
  - `sync [ids] [--diff]` refreshes the archive and rewrites INDEX.md.
  - `status` reports the archive's age.
  - `guideline REF...` prints the exact clause, e.g. `4.0`, `2.1(a)`, `3.1.2(c)`, `5.1.1(v)`.
  - `news [--days N] [--grep RE]` reads live Apple Developer News.
  - To archive a new official page, add it to `references/official/sources.json` and run `sync <id>`.
- `scripts/inspect_ipa.py <.ipa|.xcarchive|.app> [--json]` shows what review sees: identity, SDK, purpose strings and linked frameworks cross-checked both ways, entitlements, privacy manifests, export-compliance and UIScene keys. Exits 1 on errors.

## 6. Keep the skill current

This skill is a git repository. Whenever a project resolves a new rejection, ITMS error, review question or platform breakage:
- Add it to the matching `references/*.md` as reviewer wording → mechanism → fix → prevention, with the guideline or doc id. Write only the generalized principle. Project names, bundle IDs, product names and project file paths stay in that project's own docs, never here.
- If it relied on an official page that isn't archived yet, add that page to `sources.json` and run `sync`.
- Commit and push from `$SKILL`, after checking that no secrets, team IDs or device IDs are included.
