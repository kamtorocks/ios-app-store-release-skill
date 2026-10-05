# Build, version, upload, TestFlight, new iOS releases

## Contents

- Version and build numbers
- Flavors and parallel apps
- Build hygiene: the artifact is the truth
- Purpose strings and capability symmetry
- Upload: tools, auth, secrets
- After upload: processing, export compliance, privacy manifests, SDK minimums
- ITMS codes
- TestFlight
- New iOS releases
- Device evidence

## Version and build numbers

`CFBundleShortVersionString` is the marketing version (1.2.3). `CFBundleVersion` is the build number. Archived docs: cfbundleshortversionstring, cfbundleversion.

Rules that bite:
- After a marketing version is approved, it can't take new builds. The next upload needs a higher marketing version.
- A build number must be unique and increasing within its marketing version.
- `manageAppVersionAndBuildNumber = true` in the export options asks App Store Connect for the latest build of that bundle ID and version string, then writes latest + 1. Your own number wins only if it is already higher. Xcode's App Store Connect distribution and `flutter build ipa` both turn this on.
- So never inject a build number. Set the marketing version only. Failure mode: a timestamp injected "to be unique" (`date +%s`) is higher than App Store Connect's latest, so it uploads verbatim and permanently anchors that version's build line. Builds can't be deleted, and expiring them doesn't lower the baseline. The only escape is a new marketing version, because each version string starts its build count small again.
- Separate apps (flavors with different bundle IDs) have independent version lines. Never "sync" them by bumping both.
- Keep the committed version a neutral placeholder or the live store version. Set the real marketing version at build time (`--build-name`, `MARKETING_VERSION`, or the agvtool equivalent).

## Flavors and parallel apps

One bundle ID means one app per device. A TestFlight build under the production ID replaces the App Store install on every tester's device and shares the production version line.

For internal builds with extra features (hardware, debug tools, unreleased flows), use a separate bundle ID such as `com.example.app.lab`. It installs next to the store app, keeps its own version line and App Store Connect record, and can never be submitted as the production app. Setup:
- An App ID with the same capabilities (HealthKit, Push, Associated Domains, App Groups, and so on).
- Sign in with Apple configured as grouped with the primary App ID, so the same Apple user gets the same identifier in both apps.
- Backend auth accepting the new client ID (for example, an extra client ID in the Supabase Apple provider).
- A distinct icon (a ribbon or badge). The display name can stay the same.
- IAP products exist per app record. A flavor app can't sell the production products; test billing with the production ID.

When an internal build must use the production ID (real IAP products, push certificates), export it with `testFlightInternalTestingOnly = true` in ExportOptions.plist (Xcode: "TestFlight Internal Only"). Apple documents this option as preventing the build from being submitted to the App Store (distributing-for-beta-and-release). That turns "never submit this build" from a convention into a guarantee.

## Build hygiene: the artifact is the truth

- Build release artifacts only through a script, from a clean tree, with every flag set explicitly. Don't archive in the Xcode GUI after a dev run: dev-time defines persist in generated files that the archive picks up (Flutter writes `--dart-define` into `ios/Flutter/Generated.xcconfig`). A store build is "no flags" only if the script resets them.
- One flag controls one feature surface, and it defaults to the store-safe value. Retire old flags; a stale flag in a generated file becomes a silent leak.
- Flavor scripts that edit tracked files (`sed` on project.pbxproj, PlistBuddy on Info.plist, `pod install` with an environment switch rewriting Podfile.lock) leave the tree in flavor state, and it rides along in the next unrelated commit. Failure mode: an unrelated feature commit carries the flavor's Podfile.lock and Info.plist, and the default branch silently becomes flavor state. Prefer per-flavor xcconfig files with Xcode configurations or schemes, or edit a temporary copy. Otherwise pair each flavor script with a restore script and a pre-commit check:
  `git diff --quiet -- ios/Runner/Info.plist ios/Podfile.lock ios/Runner.xcodeproj/project.pbxproj || echo "flavor state in tree"`
- Verify the exact file you upload: `python3 $SKILL/scripts/inspect_ipa.py path/to/App.ipa`. Check identity, versions, purpose strings, linked frameworks and entitlements.

## Purpose strings and capability symmetry

Three things must agree in every build: a linked protected API, its `NS*UsageDescription`, and a feature that is reachable in that build.
- API linked without a string: upload rejected with ITMS-90683. The check is static: it fires when any embedded framework references the API, even if your code never calls it. At runtime the call crashes.
- String without a reachable feature: a capability the reviewer looks for and can't find (2.1), or an unjustified data request (5.1.1). A camera string kept only for a hardware setup scanner advertises the scanner.
- Feature reachable without a string: crashes when the API is called.

So a feature is only truly absent when its dependency is compiled out (conditional dependency plus a stub). When you add a permission, update every build path (store, internal, flavor) in the same change. Purpose strings say plainly what the feature does and when; reviewers read them.

## Upload: tools, auth, secrets

Tools (archived: upload-builds, distributing-for-beta-and-release): Xcode Organizer, `xcodebuild -exportArchive` with an upload destination, `xcrun altool --upload-app` / `--validate-app`, Transporter, the App Store Connect API (fastlane, CI). Run `--validate-app` before uploading to catch errors as a dry run.

Authentication for the command line:
- An Apple ID with 2FA can't use its account password, and altool can't borrow Xcode's signed-in session.
  - App-specific password: create it at appleid.apple.com > Sign-In and Security > App-Specific Passwords. Store it in the Keychain without putting it in argv: `xcrun altool --store-password-in-keychain-item --item AC_UPLOAD -u <apple-id> --app-password @env:AC_ASP`, then upload with `-p @keychain:AC_UPLOAD`. Flag spelling has changed between Xcode releases; check `xcrun altool --help`.
  - App Store Connect API key: Users and Access > Integrations > App Store Connect API, a team key with an upload-capable role. Upload with `--apiKey <KEY_ID> --apiIssuer <ISSUER_UUID>`; altool finds `AuthKey_<KEY_ID>.p8` in `./private_keys`, `~/private_keys`, `~/.private_keys` or `~/.appstoreconnect/private_keys`. APNs keys and Sign in with Apple keys are also `.p8` files but can't upload.
- Keep secrets outside every repository (`~/.appstoreconnect/`, chmod 600), and gitignore `*.p8`, `AuthKey_*.p8`, `**/private_keys/` as a backstop. Never print secret values. A "masking" expression like `${VAR%%:*}` prints the entire secret when the delimiter is missing.
- Sign in with Apple for web or REST uses a client-secret JWT signed with a `.p8`, valid for at most 6 months (`exp` no more than 15777000 s ahead; siwa-client-secret). The key doesn't expire but the JWT does. When it lapses, web sign-in fails (Supabase reports "Unable to exchange external code"). Keep a re-sign script and a calendar reminder.

## After upload: processing, export compliance, privacy manifests, SDK minimums

- Processing takes minutes to an hour. Issues arrive by email: some block the build, others are warnings that will block later.
- Export compliance: if the app uses only exempt encryption (HTTPS, OS crypto), set `ITSAppUsesNonExemptEncryption = NO` in Info.plist. Without the key, every build waits on the compliance question and TestFlight shows "Missing Compliance" until someone answers (itsappusesnonexemptencryption, export-compliance).
- Privacy manifests: SDKs ship their own `PrivacyInfo.xcprivacy`. The app needs its own manifest when the app's own code uses a required-reason API (UserDefaults, file timestamps, system boot time, disk space, active keyboards); missing declarations produce ITMS-91053 (required-reason-api). SDKs on Apple's list must ship a signed manifest (third-party-sdk-requirements). App Privacy answers in App Store Connect must match all of it (app-privacy-details).
- SDK and Xcode minimums move every spring, and the minimum deployment target moves too. Read `upcoming-requirements` live (`apple_docs.py fetch https://developer.apple.com/news/upcoming-requirements/`), because the archive may predate the latest deadline.

## ITMS codes

Upload and processing emails quote an ITMS number. Confirm the wording with a web search on the exact code; Apple adds new codes and reuses old ones.

| Code | Meaning | Usual cause → fix |
| --- | --- | --- |
| ITMS-90683 | Missing purpose string | A linked framework references a protected API → add an honest string, or compile the dependency out |
| ITMS-91053 | Missing API declaration | Required-reason API without a privacy-manifest entry → add the category and reason to the app's or SDK's manifest |
| ITMS-91061 | Missing privacy manifest | A listed third-party SDK without a manifest → update the SDK |
| ITMS-90062 | Version must be higher than the previously approved version | Re-used marketing version → bump `CFBundleShortVersionString` |
| ITMS-90189 | Redundant binary upload | Build number already used for this version → let the export auto-increment |
| ITMS-90725 | SDK version issue | Built with an SDK older than the current minimum → upgrade Xcode |
| ITMS-90717 | Invalid App Store icon | 1024 px icon has alpha/transparency → flatten |
| ITMS-90474 | Invalid bundle (iPad orientations) | iPad multitasking without all four orientations → add them, or set `UIRequiresFullScreen` |
| ITMS-90078 | Missing push notification entitlement (warning) | A push API is linked without `aps-environment` → add the capability, or drop the dependency |
| ITMS-90338 | Non-public API usage | Private selectors, often from an SDK → update or remove the SDK |

## TestFlight

- Internal testers are App Store Connect users on the team, up to 100. Builds are available once processed, with no review. This is the place for feature-gated or hardware builds.
- External testers (up to 10,000, groups or public link) need Beta App Review for the first build of each version. Treat it like App Review: no unshippable capabilities.
- Builds expire after 90 days.
- Uploading routes by bundle ID: a flavor IPA lands in the flavor's app record automatically.
- Remember that a production-ID TestFlight build replaces the store app on the tester's device.

## New iOS releases

A live app can break on a new iOS with no change on your side. Apple announces these one or more releases ahead, and they then become hard failures.

Example: iOS 27 enforces UIScene adoption. An app without it traps while the scene is being created, before any app code runs:

```
___UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption_block_invoke
EXC_BREAKPOINT (SIGTRAP) ← -[UIApplication workspace:didCreateScene:...] ← UIApplicationMain
```

Every existing build, including the version live on the App Store, crashes at launch on iOS 27. The fix needs both parts (tn3187-uiscene-lifecycle):
1. A scene delegate exists: native apps adopt `UIWindowSceneDelegate`; cross-platform apps need a framework version that ships one (Flutter >= 3.47 `FlutterSceneDelegate`).
2. Info.plist declares `UIApplicationSceneManifest` with `UISceneDelegateClassName` pointing at it.

Doing only part 1 changes nothing, which makes "upgrade the framework" look like the wrong direction. After migrating, re-test the lifecycle-sensitive paths: foreground and background, deep links and Universal Links, notifications, IAP, WebView, state restoration.

Cadence:
- June (WWDC betas): install the shipping App Store build on the beta, read the iOS release notes for deprecations, and grep `news`.
- July and August: fix on a branch; check that your frameworks and plugins support the new SDK. Dead packages block forced upgrades; replace them early.
- September (RC): submit before public release. Request an expedited review if users are already broken.
- Watch: `python3 $SKILL/scripts/apple_docs.py news --days 120 --grep "require|deadline|SDK|Xcode|iOS 2"`.

## Device evidence

The only authoritative evidence for a crash on a real device is its crash report:
- On the device: Settings > Privacy & Security > Analytics & Improvements > Analytics Data.
- Xcode: Devices and Simulators > View Device Logs; Organizer > Crashes (TestFlight and App Store).
- TestFlight tester crash feedback.
- The crash log attached to an App Review rejection.

Signals that mislead device debugging (archived: crash-reports):
- A debug build launched without the debugger dies on iOS 14+ for some runtimes (Flutter debug uses JIT): "signal 5" there is unrelated to your bug.
- `devicectl device process launch --console` exiting with 0 means the console session ended, not that the app is healthy.
- An app launched by devicectl without foreground focus is suspended and reclaimed, so A/B tests launched that way measure focus, not crashes.
- When the tooling can't pull logs, ask the device owner for the crash report rather than inferring from indirect signals.
