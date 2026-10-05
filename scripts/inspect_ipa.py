#!/usr/bin/env python3
"""Show what App Review will see in a built app — inspect the artifact, not the source tree.

Usage
  inspect_ipa.py PATH [--json]
  PATH: an .ipa, an .xcarchive, or a .app bundle.

Reports identity (bundle id, versions, SDK/Xcode, min OS, device family), purpose
strings, entitlements, privacy manifests, export-compliance and UIScene keys, and the
privacy-sensitive system frameworks each binary links. Then cross-checks both ways:
  linked framework without its purpose string  -> ITMS-90683 at upload / crash at runtime
  purpose string without a linked framework     -> declared capability the reviewer will
                                                   look for (Guideline 2.1 / 5.1.1)
macOS only (uses otool and codesign from the Xcode command line tools).
"""
import argparse
import json
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# framework -> purpose-string keys that satisfy it (any one). Frameworks whose mere
# linkage does not imply a protected resource (AVFoundation, Photos, Network) are
# reported but not cross-checked.
FRAMEWORK_KEYS = {
    "CoreBluetooth": ["NSBluetoothAlwaysUsageDescription"],
    "CoreLocation": ["NSLocationWhenInUseUsageDescription", "NSLocationAlwaysAndWhenInUseUsageDescription"],
    "HealthKit": ["NSHealthShareUsageDescription", "NSHealthUpdateUsageDescription"],
    "Contacts": ["NSContactsUsageDescription"],
    "EventKit": ["NSCalendarsFullAccessUsageDescription", "NSCalendarsWriteOnlyAccessUsageDescription",
                 "NSCalendarsUsageDescription", "NSRemindersFullAccessUsageDescription", "NSRemindersUsageDescription"],
    "AppTrackingTransparency": ["NSUserTrackingUsageDescription"],
    "CoreMotion": ["NSMotionUsageDescription"],
    "Speech": ["NSSpeechRecognitionUsageDescription"],
    "LocalAuthentication": ["NSFaceIDUsageDescription"],
    "CoreNFC": ["NFCReaderUsageDescription"],
    "HomeKit": ["NSHomeKitUsageDescription"],
    "NearbyInteraction": ["NSNearbyInteractionUsageDescription"],
    "SensorKit": ["NSSensorKitUsageDescription"],
}
REPORT_ONLY = {"AVFoundation", "Photos", "PhotosUI", "MediaPlayer", "StoreKit", "AuthenticationServices",
               "UserNotifications", "NetworkExtension", "ExternalAccessory", "CallKit", "PushKit",
               "WebKit", "SafariServices", "CloudKit", "MessageUI", "Intents", "ActivityKit"}
# purpose key -> frameworks that would back it (for the reverse check)
KEY_FRAMEWORKS = {
    "NSBluetoothAlwaysUsageDescription": ["CoreBluetooth"],
    "NSBluetoothPeripheralUsageDescription": ["CoreBluetooth"],
    "NSLocationWhenInUseUsageDescription": ["CoreLocation"],
    "NSLocationAlwaysAndWhenInUseUsageDescription": ["CoreLocation"],
    "NSLocationAlwaysUsageDescription": ["CoreLocation"],
    "NSHealthShareUsageDescription": ["HealthKit"],
    "NSHealthUpdateUsageDescription": ["HealthKit"],
    "NSCameraUsageDescription": ["AVFoundation", "VisionKit"],
    "NSMicrophoneUsageDescription": ["AVFoundation", "AVFAudio", "Speech"],
    "NSContactsUsageDescription": ["Contacts"],
    "NSUserTrackingUsageDescription": ["AppTrackingTransparency"],
    "NSMotionUsageDescription": ["CoreMotion"],
    "NSSpeechRecognitionUsageDescription": ["Speech"],
    "NSFaceIDUsageDescription": ["LocalAuthentication"],
    "NFCReaderUsageDescription": ["CoreNFC"],
    "NSHomeKitUsageDescription": ["HomeKit"],
    "NSPhotoLibraryUsageDescription": ["Photos", "PhotosUI", "UIKit"],
}
SYS_FW = re.compile(r"/System/Library/(?:Private)?Frameworks/([A-Za-z0-9_]+)\.framework/")


def run(cmd):
    p = subprocess.run(cmd, capture_output=True)
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")


def locate_app(path, tmp):
    p = Path(path)
    if p.suffix == ".app" and p.is_dir():
        return p
    if p.suffix == ".xcarchive" and p.is_dir():
        apps = list((p / "Products" / "Applications").glob("*.app"))
        if apps:
            return apps[0]
    if p.suffix == ".ipa" and p.is_file():
        with zipfile.ZipFile(p) as z:
            z.extractall(tmp)
        apps = list((Path(tmp) / "Payload").glob("*.app"))
        if apps:
            return apps[0]
    sys.exit("no .app found in " + path)


def binaries(app):
    info = plistlib.loads((app / "Info.plist").read_bytes())
    out = [("app", app / info["CFBundleExecutable"])]
    for fw in sorted((app / "Frameworks").glob("*.framework")):
        fi = fw / "Info.plist"
        exe = plistlib.loads(fi.read_bytes()).get("CFBundleExecutable", fw.stem) if fi.exists() else fw.stem
        out.append((fw.name, fw / exe))
    for ext in sorted((app / "PlugIns").glob("*.appex")):
        ei = plistlib.loads((ext / "Info.plist").read_bytes())
        out.append((ext.name, ext / ei["CFBundleExecutable"]))
    return [(n, b) for n, b in out if b.exists()]


def linked_frameworks(binary):
    rc, out, _ = run(["otool", "-L", str(binary)])
    if rc != 0:
        return set()
    return set(SYS_FW.findall(out.decode("utf-8", "replace")))


def entitlements(app):
    rc, out, _ = run(["codesign", "-d", "--entitlements", ":-", str(app)])
    if rc != 0 or not out.strip():
        return {}
    try:
        return plistlib.loads(out)
    except Exception:
        return {}


def privacy_manifests(app):
    found = []
    for pm in sorted(app.rglob("PrivacyInfo.xcprivacy")):
        try:
            d = plistlib.loads(pm.read_bytes())
        except Exception:
            found.append({"path": str(pm.relative_to(app)), "error": "unreadable"})
            continue
        apis = {}
        for item in d.get("NSPrivacyAccessedAPITypes", []):
            cat = item.get("NSPrivacyAccessedAPIType", "?").replace("NSPrivacyAccessedAPICategory", "")
            apis[cat] = item.get("NSPrivacyAccessedAPITypeReasons", [])
        found.append({
            "path": str(pm.relative_to(app)),
            "tracking": d.get("NSPrivacyTracking", False),
            "tracking_domains": d.get("NSPrivacyTrackingDomains", []),
            "collected_types": [c.get("NSPrivacyCollectedDataType", "?").replace("NSPrivacyCollectedDataType", "")
                                for c in d.get("NSPrivacyCollectedDataTypes", [])],
            "required_reason_apis": apis,
        })
    return found


def inspect(path):
    tmp = tempfile.mkdtemp(prefix="inspect-ipa-")
    try:
        app = locate_app(path, tmp)
        info = plistlib.loads((app / "Info.plist").read_bytes())
        per_binary = {name: sorted(linked_frameworks(b)) for name, b in binaries(app)}
        all_fw = set().union(*[set(v) for v in per_binary.values()]) if per_binary else set()
        purpose = {k: v for k, v in info.items() if k.endswith("UsageDescription") or k == "NFCReaderUsageDescription"}
        ents = entitlements(app)
        manifests = privacy_manifests(app)

        findings = []
        for fw, keys in FRAMEWORK_KEYS.items():
            if fw in all_fw and not any(k in purpose for k in keys):
                who = [n for n, fws in per_binary.items() if fw in fws]
                findings.append(("ERROR", "{} linked by {} but none of {} declared -> ITMS-90683 at upload; crash when the API runs"
                                 .format(fw, ", ".join(who), "/".join(keys))))
        for key in purpose:
            backers = KEY_FRAMEWORKS.get(key)
            if backers and not any(f in all_fw for f in backers):
                findings.append(("WARN", "{} declared but no binary links {} -> a capability App Review will look for "
                                 "and cannot find (2.1 / 5.1.1). Remove it unless a plugin needs it at runtime."
                                 .format(key, "/".join(backers))))
        if "CoreBluetooth" in all_fw:
            findings.append(("WARN", "CoreBluetooth is linked: reviewers treat this as a hardware-accessory app and may "
                             "request a device demo video (Guideline 2.1) unless the feature is reachable and documented."))
        if "ITSAppUsesNonExemptEncryption" not in info:
            findings.append(("WARN", "ITSAppUsesNonExemptEncryption absent -> every build waits on the export-compliance "
                             "question in App Store Connect (TestFlight shows 'Missing Compliance')."))
        if "UIApplicationSceneManifest" not in info:
            findings.append(("ERROR", "UIApplicationSceneManifest absent -> no UIScene adoption; iOS 27+ traps at launch (TN3187)."))
        if 2 in info.get("UIDeviceFamily", []):
            msg = "iPad supported (UIDeviceFamily has 2) -> iPad screenshots required and the app is reviewed on iPad."
            if not info.get("UIRequiresFullScreen") and len(info.get("UISupportedInterfaceOrientations~ipad", [])) < 4:
                msg += " iPad multitasking needs all 4 orientations or UIRequiresFullScreen=YES (ITMS-90474)."
            findings.append(("INFO", msg))
        if not any(m["path"] == "PrivacyInfo.xcprivacy" for m in manifests):
            findings.append(("INFO", "No app-level PrivacyInfo.xcprivacy. Needed if the app's own code uses a "
                             "required-reason API (UserDefaults, file timestamps, boot time, disk space, keyboards) -> ITMS-91053."))
        aps = ents.get("aps-environment")
        if aps and aps != "production":
            findings.append(("WARN", "aps-environment = {} (expected production in a distribution build)".format(aps)))
        if ents.get("get-task-allow"):
            findings.append(("ERROR", "get-task-allow = true -> development-signed; not an App Store build."))

        return {
            "path": str(path),
            "bundle_id": info.get("CFBundleIdentifier"),
            "display_name": info.get("CFBundleDisplayName") or info.get("CFBundleName"),
            "version": info.get("CFBundleShortVersionString"),
            "build": info.get("CFBundleVersion"),
            "min_os": info.get("MinimumOSVersion"),
            "sdk": info.get("DTSDKName"),
            "xcode": info.get("DTXcode"),
            "xcode_build": info.get("DTXcodeBuild"),
            "device_family": info.get("UIDeviceFamily"),
            "export_compliance_key": info.get("ITSAppUsesNonExemptEncryption"),
            "scene_manifest": "UIApplicationSceneManifest" in info,
            "background_modes": info.get("UIBackgroundModes", []),
            "url_schemes": [s for t in info.get("CFBundleURLTypes", []) for s in t.get("CFBundleURLSchemes", [])],
            "purpose_strings": purpose,
            "entitlements": ents,
            "linked_system_frameworks": per_binary,
            "privacy_manifests": manifests,
            "findings": [{"level": l, "message": m} for l, m in findings],
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def show(r):
    w = print
    w("== Identity")
    for k in ("bundle_id", "display_name", "version", "build", "min_os", "sdk", "xcode", "device_family"):
        w("  {:<15} {}".format(k, r[k]))
    w("  {:<15} {}".format("export key", r["export_compliance_key"]))
    w("  {:<15} {}".format("UIScene", "declared" if r["scene_manifest"] else "MISSING"))
    if r["background_modes"]:
        w("  {:<15} {}".format("bg modes", ", ".join(r["background_modes"])))
    w("\n== Purpose strings ({})".format(len(r["purpose_strings"])))
    for k, v in sorted(r["purpose_strings"].items()):
        w("  {}: {}".format(k, v if len(v) < 110 else v[:107] + "..."))
    w("\n== Entitlements")
    for k, v in sorted(r["entitlements"].items()):
        w("  {} = {}".format(k, json.dumps(v)))
    w("\n== Privacy-relevant system frameworks by binary")
    watch = set(FRAMEWORK_KEYS) | REPORT_ONLY
    for name, fws in r["linked_system_frameworks"].items():
        hits = [f for f in fws if f in watch]
        if hits:
            w("  {:<40} {}".format(name, ", ".join(hits)))
    w("\n== Privacy manifests ({})".format(len(r["privacy_manifests"])))
    for m in r["privacy_manifests"]:
        apis = ", ".join("{}[{}]".format(k, ",".join(v)) for k, v in m.get("required_reason_apis", {}).items())
        w("  {}{}".format(m["path"], "  tracking=YES" if m.get("tracking") else ""))
        if apis:
            w("      APIs: " + apis)
    w("\n== Findings")
    if not r["findings"]:
        w("  none")
    for f in sorted(r["findings"], key=lambda f: ["ERROR", "WARN", "INFO"].index(f["level"])):
        w("  [{}] {}".format(f["level"], f["message"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not shutil.which("otool") or not shutil.which("codesign"):
        sys.exit("needs otool and codesign (xcode-select --install)")
    r = inspect(a.path)
    if a.json:
        print(json.dumps(r, indent=2, default=str))
    else:
        show(r)
    sys.exit(1 if any(f["level"] == "ERROR" for f in r["findings"]) else 0)


if __name__ == "__main__":
    main()
