# Flutter and other cross-platform stacks on iOS

The general rules live in build-and-upload.md. This file covers how each one shows up in Flutter, with short notes for other stacks at the end.

## Contents

- Dart defines leak through Generated.xcconfig
- Plugins are linked whether or not Dart calls them
- Compiling a native capability out
- Version and build numbers with `flutter build ipa`
- UIScene (iOS 27) and the lifecycle callbacks that move
- Universal Links with app_links
- Sign in with Apple
- Forced upgrades and dead packages
- Device and simulator quirks
- Other stacks

## Dart defines leak through Generated.xcconfig

`flutter run --dart-define=X=true` writes `DART_DEFINES` (each define base64-encoded) into `ios/Flutter/Generated.xcconfig`. A later Product > Archive in Xcode reuses them, so a dev flag ships ON in the store build. This is how a gated feature reaches the reviewer.

- Build store IPAs only with `flutter build ipa` from a script. It regenerates the file with exactly the defines you pass. Run `flutter clean` first after a dev session.
- Read flags as `bool.fromEnvironment('X', defaultValue: false)`, with the store-safe default.
- Inspect what is baked in:
  `grep DART_DEFINES ios/Flutter/Generated.xcconfig | sed 's/^DART_DEFINES=//' | tr ',' '\n' | while read d; do echo "$d" | base64 -D; echo; done`

## Plugins are linked whether or not Dart calls them

Every plugin in `pubspec.yaml` has its iOS code compiled and its frameworks linked, so a Dart `if` doesn't remove it. A BLE plugin puts CoreBluetooth in the store binary even if the screen that uses it is gated off. Consequences:
- ITMS-90683 demands purpose strings for APIs the plugin references, even if you never call them.
- Reviewers see the capability (see the hardware entry in rejection-playbook.md).
- Some plugins compile features in or out with macros. `permission_handler` uses `GCC_PREPROCESSOR_DEFINITIONS` entries such as `PERMISSION_CAMERA=1` in the Podfile `post_install`; check its README for the current default. If a permission is compiled in but unused, it triggers purpose-string demands; if it is compiled out but used, the request silently returns denied.
- Some plugins reference APIs you don't use (Always location, HealthKit write) and require their keys. Read the plugin README and write honest strings, or choose a plugin that doesn't drag the API in.

## Compiling a native capability out

To keep a capability out of the store binary, it must not be a pub plugin dependency of the store build. Keep it as native code in the app target behind a conditional pod:

```ruby
# ios/Podfile, inside target 'Runner'
pod 'VendorHardwareSDK' if ENV['APP_HARDWARE'] == '1'
```

```swift
// ios/Runner/HardwarePlugin.swift
#if canImport(VendorHardwareSDK)
import VendorHardwareSDK
import CoreBluetooth
// real implementation registers the method channel
#else
// stub: registers the same channel, answers "unavailable", imports nothing sensitive
#endif
```

Then:
- The hardware build script exports `APP_HARDWARE=1`, runs `pod install`, adds the purpose strings, and passes `--dart-define=APP_HARDWARE=true`.
- The store build script runs `pod install` without it, strips the strings, and passes no define.
- Each script leaves Podfile.lock and Info.plist in its own state, so restore or guard before committing (build-and-upload.md, "Build hygiene").
- Verify with `inspect_ipa.py`: the store IPA lists no CoreBluetooth in any binary.

## Version and build numbers with `flutter build ipa`

- `flutter build ipa` writes ExportOptions.plist with `method = app-store-connect` and `manageAppVersionAndBuildNumber = true`. The build number then comes from App Store Connect (latest + 1 for that version string).
- In the pubspec, `version: x.y.z+N` sets the marketing version from `x.y.z` (overridable with `--build-name`). `N` is only a placeholder: it is replaced unless it is higher than App Store Connect's latest. Never pass `--build-number`.
- For a custom export, such as an internal-only build under the production ID, use `flutter build ipa --export-options-plist=ios/ExportOptions-internal.plist` with `testFlightInternalTestingOnly` set to true.

## UIScene (iOS 27) and the lifecycle callbacks that move

Flutter 3.47 is the first version that ships `FlutterSceneDelegate`. You need both the engine floor (`environment: flutter: '>=3.47.0'` in the pubspec) and the manifest:

```xml
<key>UIApplicationSceneManifest</key>
<dict>
  <key>UIApplicationSupportsMultipleScenes</key><false/>
  <key>UISceneConfigurations</key>
  <dict>
    <key>UIWindowSceneSessionRoleApplication</key>
    <array>
      <dict>
        <key>UISceneClassName</key><string>UIWindowScene</string>
        <key>UISceneConfigurationName</key><string>flutter</string>
        <key>UISceneDelegateClassName</key><string>FlutterSceneDelegate</string>
        <key>UISceneStoryboardFile</key><string>Main</string>
      </dict>
    </array>
  </dict>
</dict>
```

Once scenes are adopted, UIKit delivers URL and user-activity events to the scene delegate, not the app delegate:
- A cold-start link arrives in `scene(_:willConnectTo:options:)`.
- A custom-scheme URL arrives in `scene(_:openURLContexts:)`.
- A Universal Link arrives in `scene(_:continue:)`.

AppDelegate overrides of `application(_:open:options:)` or `application(_:continue:restorationHandler:)` silently stop being called. Plugins that rely on those callbacks (deep links, auth redirects, notification taps) must support the scene lifecycle; check each plugin's changelog. After migrating, test on a device: cold-start and warm Universal Links, custom schemes, notification taps, OAuth or Sign in with Apple redirects, IAP, foreground and background.

## Universal Links with app_links

- Pre-scene apps: some app_links versions return false from `continueUserActivity` after capturing the link, so iOS also opens the URL in Safari. The fix was an AppDelegate override that calls super and then returns true for `NSUserActivityTypeBrowsingWeb`. After UIScene adoption that override is never called (see above), so re-verify.
- Set `FlutterDeepLinkingEnabled = false` when a package owns link routing, so the engine doesn't route the link a second time.
- AASA: serve JSON at `https://<domain>/.well-known/apple-app-site-association` with no redirect, and add the `applinks:<domain>` entitlement (associated-domains). On Next.js, serve it from a route handler plus a rewrite so the dotted path is registered reliably.

## Sign in with Apple

- `sign_in_with_apple` returns `givenName` and `familyName` only on the first authorization. Persist them right away (for example into the auth user's `full_name` metadata) and prefill onboarding from them (Guideline 4.0).
- The package's `SignInWithAppleButton` is drawn with CustomPaint; it isn't Apple's control. Embed `ASAuthorizationAppleIDButton` as a platform view (a `UiKitView` backed by a `FlutterPlatformViewFactory`), with type `.continue` or `.signIn`, black or white style per theme, and corner radius set to half the height for a pill.
- A separate bundle ID (flavor) needs Sign in with Apple grouped with the primary App ID, and the backend must accept its client ID.

## Forced upgrades and dead packages

Apple forces engine upgrades on its own schedule (UIScene, SDK minimums). A package that no longer compiles on the new engine then blocks a release that has a deadline. Example: an icon package abandoned for two years stopped compiling when the framework made a base class final; the fix was generating plain constants and bundling the font. Run `flutter pub outdated` and check last-publish dates each spring, and replace abandoned packages before you need the upgrade.

## Device and simulator quirks

- Flutter debug builds use JIT, and on iOS 14+ they die when launched without `flutter run` or a debugger attached ("signal 5"). Use profile or release builds for standalone launches.
- Wireless devices: if `flutter run -d` can't attach, use `xcrun devicectl device install app --device <udid> build/ios/iphoneos/Runner.app` and then `xcrun devicectl device process launch --device <udid> <bundle-id>`. Mind the evidence caveats in build-and-upload.md.
- No simulator destinations in Xcode: the iOS platform isn't downloaded (`xcodebuild -downloadPlatform iOS`).
- iOS 26+ simulator runtimes are arm64-only, so a vendored static library without an arm64-simulator slice won't link and `EXCLUDED_ARCHS=arm64` no longer helps. Rebuild it as an XCFramework with a simulator slice. As a last resort, retag the device slice's `LC_BUILD_VERSION` platform to the simulator.

## Other stacks

The mechanisms are the same; only the files differ. Inspect the IPA regardless.
- React Native / Expo: environment values are baked in at bundle time, and autolinked native modules are linked regardless of JS usage. Use build profiles or config plugins to drop modules and Info.plist keys from the store profile. Expo's `ios.infoPlist` is the source of purpose strings.
- Capacitor / Cordova: plugins add frameworks and Info.plist keys at sync time. Review the generated native project, not the web code.
- Native Swift: use build configurations plus xcconfig per flavor, and `#if` compilation conditions. Prefer conditional SPM or pod dependencies to runtime flags.
