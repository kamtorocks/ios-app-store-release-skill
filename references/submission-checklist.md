# Submission checklist

Run this top to bottom before each submission, first release or update. Each line names where the rule comes from. "Inspect" means `python3 $SKILL/scripts/inspect_ipa.py <the IPA you upload>`.

## 0. Ground truth

- [ ] `apple_docs.py status` shows nothing stale; `news --days 90` has no requirement you haven't met (SDK/Xcode minimum, deployment target, age rating, privacy manifests).
- [ ] The review guidelines diff since your last release is read (`sync review-guidelines --diff`).

## 1. Binary (inspect the artifact)

- [ ] Built by the store script from a clean tree; no dev flags baked in (build-and-upload.md, "Build hygiene").
- [ ] Bundle ID, marketing version (higher than the last approved one), auto-managed build number.
- [ ] SDK/Xcode meet the current minimum (upcoming-requirements).
- [ ] `UIApplicationSceneManifest` present and the scene delegate wired (tn3187-uiscene-lifecycle).
- [ ] Linked frameworks, purpose strings and reachable features agree in both directions; no capability the store build doesn't use (inspect findings).
- [ ] Entitlements match capabilities actually used: `aps-environment = production`, no `get-task-allow`.
- [ ] `ITSAppUsesNonExemptEncryption` set, or export documentation prepared (export-compliance).
- [ ] App privacy manifest present if the app's own code uses required-reason APIs; SDK manifests present (required-reason-api).
- [ ] Device family decided. iPad support means iPad review, iPad screenshots, and all four orientations or `UIRequiresFullScreen`.
- [ ] Built for internal-only purposes? Then it was exported as TestFlight Internal Only, or under a separate bundle ID, and is not this submission.

## 2. Behaviour the reviewer will exercise

- [ ] Fresh install on the newest public iOS (and a beta in June–September): launch reaches an interactive screen at once; no splash that waits on a hidden tap (2.1(a)).
- [ ] Demo account works end to end, isn't allowlisted or rate-limited, and has the subscription state you want reviewed; a brand-new account also works (2.1(a)).
- [ ] Empty states (no data, no Health history, no Watch, permission denied) explain themselves.
- [ ] Every visible button does something or explains why it can't. No placeholder or "coming soon" content, no broken links.
- [ ] Permissions requested in context. Pre-alert screens have a single "Continue"/"Next" button; nothing is requested at launch (5.1.1(iv), hig-privacy).
- [ ] Personal data sent to any third party (analytics, AI providers) is disclosed in-app with explicit consent before the first send (5.1.2(i)).
- [ ] Account deletion in-app actually deletes; Sign in with Apple tokens are revoked (5.1.1(v), tn3194-siwa-account-deletion).
- [ ] Sign in with Apple uses the system button and never asks for name or email afterwards (4.0, hig-sign-in-with-apple). Third-party login offered → an equivalent private option exists (4.8).
- [ ] Review prompts use the system API only, with no incentive (5.6.1).

## 3. In-app purchase (iap-subscriptions.md)

- [ ] Paid Apps Agreement, banking and tax active; products Ready to Submit; the first IAP of each type attached to this version.
- [ ] A sandbox purchase on the production backend succeeds, including expired or re-delivered transactions.
- [ ] Paywall: billed price most prominent; intro offer secondary and always shown; auto-renew and cancel terms; working Terms and Privacy links; Restore; no fake urgency (3.1.2).
- [ ] Every purchase failure is visible to the user.
- [ ] Purchase surfaces hidden if the chain isn't complete, and no IAP submitted in that case (2.1(b)).

## 4. Metadata and assets (App Store Connect)

- [ ] Name ≤30 chars, subtitle ≤30, keywords ≤100 bytes (CJK characters take 3 bytes each in UTF-8), promotional text ≤170, description ≤4000; no prices, competitors or trademarks (2.3.7, platform-version-information, app-information).
- [ ] Screenshots: required sizes (screenshot-specifications), no alpha, the real app in use, only features in this binary (2.3.3).
- [ ] Copy makes no medical diagnose/treat/cure claims unless the app is a regulated medical product (1.4.1).
- [ ] Privacy Policy URL live and complete: every data type, every third party including AI providers, health data, deletion (5.1.1(i)). Support URL live with contact details.
- [ ] Terms of Use: Apple standard EULA, or a custom EULA containing Apple's minimum terms. Linked in the description for subscriptions.
- [ ] App Privacy answers match the binary, the SDKs and the server (app-privacy-details).
- [ ] Age rating questionnaire answered under the current system (age-ratings).
- [ ] Copyright holder equals the developer account's legal entity.

## 5. App Review Information

- [ ] Demo account plus steps to reach each non-obvious feature and the paywall.
- [ ] What each permission is for; what needs hardware and how to review without it (or a demo video attached).
- [ ] Anything configured but not reachable, and why.
- [ ] Contact phone and email monitored during review.

## 6. After submission

- [ ] Release mode chosen (manual, automatic, phased).
- [ ] Someone watches App Store Connect messages; reply within a day.
- [ ] Rejected → rejection-playbook.md. Approved → reset any build-time state (flavor files, version placeholder) and commit.
