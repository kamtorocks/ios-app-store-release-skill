# Rejection playbook

Each entry: reviewer wording → mechanism (what in the binary, metadata or backend produced it) → fix → prevention. Pull the current guideline text before replying: `python3 $SKILL/scripts/apple_docs.py guideline <ref>`.

## Contents

- Triage: fix class, reply vs new build, appeal
- 2.1 Information Needed: hardware / accessory demo video
- 2.1(a) Completeness: hang, crash, can't sign in, empty states
- 2.1(b) In-app purchase not working or not found
- 2.3 Metadata and screenshots
- 3.1.1 / 3.1.3 Payment routes and Restore
- 3.1.2 Subscription disclosure, price prominence, false urgency
- 4.0 Sign in with Apple asks for name or email again
- 4.2 Minimum functionality
- 4.8 Login services
- 5.1.1(i) Privacy policy
- 5.1.1(iv) Permission requests
- 5.1.1(v) Account deletion
- 5.1.2(i) Sharing data with third parties, including AI providers
- 5.1.3 Health data
- 5.6.1 Review prompts
- Reply templates

## Triage

1. List every guideline in the message. Fix all of them in one round: repeated rejections for the same guideline make later reviews slower (Review Guidelines, "After You Submit").
2. Classify the fix:
   - Metadata only: edit in App Store Connect, reply, resubmit the same build.
   - Server only: deploy, reply explaining the change; the same build can be re-reviewed. Example: a 2.1(b) "subscription expired" caused by server verify logic needs no new binary.
   - Binary: new build. Bump nothing but what the build pipeline requires (see build-and-upload.md).
3. Reproduce as the reviewer: release build (TestFlight), fresh install, latest public iOS, the demo account from Review Notes, a sandbox Apple Account, no prior app data, and iPad too if the app supports iPad.
4. Reply rather than argue. Appeal (App Review Board) only when the app already complies and the reviewer misread it.
5. Live app with an urgent bug fix blocked by an unrelated guideline: ask for the "Bug Fix Submissions" path in the reply and commit to fixing the guideline issue in the next submission. Legal and safety issues are excluded.
6. Time-critical: request an expedited review (link in the guidelines' "After You Submit"). Reserve it for real emergencies such as a crash affecting all users.

## 2.1 Information Needed: hardware / accessory demo video

Reviewer: asks for a demo video of the app working with a physical device, or says they could not review a hardware feature.

Mechanism: the binary presents hardware-accessory capability. Any one of these is enough:
- a reachable flow that pairs, scans or provisions (Bluetooth, Wi-Fi provisioning, QR setup scan);
- `NSBluetooth*UsageDescription`, or `NSCameraUsageDescription` used only by a setup scanner;
- CoreBluetooth (or ExternalAccessory, NetworkExtension hotspot APIs) linked by the app or any embedded framework.

Two legitimate exits:

A. Ship the hardware feature. In App Review Information, attach a video on a real device with the real accessory (pairing through core function), describe what can be tested without the device, and make sure the device-free path works.

B. Ship without it. Compile it out of the store build. Each half-measure leaves one signal behind and costs a full review round. The typical sequence:

| Round | Change | Result |
| --- | --- | --- |
| 1 | Hardware UI behind a feature flag | A dev flag leaked into the archive; the reviewer reached the Bluetooth prompt. Rejected. |
| 2 | Removed the Bluetooth purpose strings | The framework was still linked through a pod. Upload rejected: ITMS-90683. |
| 3 | Restored minimal, honest purpose strings | The binary still linked CoreBluetooth. Demo video requested again. |
| 4 | Pod included only when `HARDWARE=1`, `#if canImport(...)` stub, no purpose strings, flag defaults off | Approved. |

Prevention: run `scripts/inspect_ipa.py` on the exact IPA you upload. A store IPA without the feature has no CoreBluetooth in any binary, no Bluetooth or camera keys, and no hardware in its screenshots or description.

## 2.1(a) Completeness: hang, crash, can't sign in, empty states

- "Hangs on the splash screen" or "no response at launch": an in-app splash that waits on a timer or an invisible tap target. Show an interactive screen right away; the native launch screen carries the brand. A full-screen invisible tap target enabled after a delay reads as a dead app.
- Crash: reviewers run the newest public iOS, often a release that shipped days earlier. Symbolicate the crash log attached to the rejection. Lifecycle changes in a new major iOS can crash the binary before your code runs (iOS 27 UIScene, see build-and-upload.md).
- Login: the demo account must stay valid, skip rate limits, allowlists and 2FA, and unlock every reviewable feature. If Sign in with Apple is offered, the reviewer may create a fresh account. Make sure a brand-new account reaches every feature, or say in the notes which account to use. Failure mode: an allowlist keyed by user ID misses the reviewer, because Sign in with Apple created a second identity for the same person.
- Backend: live and reachable from the reviewer's region during review, not geo-blocked or behind VPN.
- Empty data: reviewers have no history, no Apple Watch and often an empty Health store. Empty states must explain themselves and offer a next step, not look broken.
- Placeholder content, "coming soon" sections, and links that 404 count as incomplete.

## 2.1(b) In-app purchase not working or not found

Reviewer: purchase failed, an error appeared, nothing happened on tap, or configured products are missing from the app.

Check in this order:
1. Products don't load. The Paid Apps Agreement, banking or tax setup isn't active; the product isn't Ready to Submit; the first IAP of each type isn't attached to this app version (the first item of each type must ride with a version); product ID or bundle ID mismatch (watch flavor builds).
2. The server rejects sandbox. Reviewers buy with a sandbox account in your production build against your production backend. Accept sandbox-environment transactions; never route by "production build means production receipts".
3. The server rejects stale transactions. Sandbox renews on an accelerated clock (minutes per period) and StoreKit re-delivers old transactions, so a receipt can arrive already expired. Rejecting `expiresDate <= now` at verify time shows the reviewer "subscription expired". Record the transaction; decide access when entitlements are read.
4. Silent failure. A purchase call that returns false, or a verify failure swallowed as "offline", leaves a dead button. Every failure path needs a visible message.
5. Unfinished purchase UI. If purchasing isn't wired end to end, hide every purchase surface and don't submit the IAP, or explain in the notes. Under 2.1(b), what is configured and what is reachable must agree.

The fix is often server-only, in which case reply and re-review the same build. Details: iap-subscriptions.md.

## 2.3 Metadata and screenshots

- Screenshots show the app in use, not title art, a login page or a splash (2.3.3), and only what this binary does: no gated, hidden or hardware features.
- Name, subtitle and keywords carry no pricing, competitor names or trademarks (2.3.7).
- Health and wellness copy must not claim to diagnose, treat or cure. Medical claims draw 1.4.1 scrutiny and a Medical age-rating answer.
- Review Notes explain anything non-obvious: test steps, demo account, why a permission is needed, what needs hardware.

## 3.1.1 / 3.1.3 Payment routes and Restore

- Unlocking features or digital content uses in-app purchase. External purchase links and calls to action are allowed only where 3.1.1(a), 3.1.3 or storefront-specific rules permit them; these differ by region and change often, so read the live text.
- A web checkout that exists for browsers must not appear inside the app.
- Restorable purchases need a working Restore control (3.1.1), placed inside the purchase flow as well as Settings.

## 3.1.2 Subscription disclosure, price prominence, false urgency

Reviewer: missing title, length or price; non-functional Terms or Privacy links; the introductory price is more prominent than the billed amount; misleading offer.

Required, per 3.1.2(c) and Schedule 2 of the Developer Program License Agreement:
- In the purchase flow: subscription name, duration, price (and price per unit where relevant), what the user gets, and functional links to Terms of Use (EULA) and Privacy Policy. Restore and auto-renew/cancel terms belong here too.
- In metadata: the Privacy Policy URL field, plus a Terms of Use link in the description or a custom EULA set in App Store Connect.

Prominence: the recurring amount the user will be billed is the largest, clearest price on the screen. An introductory price is secondary text and is always shown, because StoreKit grants it to every eligible new subscriber; don't show it only inside your own funnel window.

False urgency: a countdown implying the offer expires when it doesn't is a trick under 3.1.2(a) ("trick users into purchasing a subscription under false pretenses").

Prevention: one checkout component renders the legal footer in every state (loading, error, purchased). Never duplicate the paywall.

## 4.0 Sign in with Apple asks for name or email again

Reviewer: "requires users to provide their name and/or email address after using Sign in with Apple".

Mechanism: onboarding still has a required name or email field. Apple returns name and email only on the first authorization; later sign-ins return null. If you don't persist them then, you can never prefill them.

Fix: on first authorization, store given/family name (local, plus server profile metadata), prefill, and auto-complete the step. Never require an email after Sign in with Apple.

Related: use Apple's own button (`ASAuthorizationAppleIDButton`, or the SwiftUI equivalent), not a redrawn logo; see hig-sign-in-with-apple. Some cross-platform plugins draw the button with custom painting; embed the system button through a platform view instead.

## 4.2 Minimum functionality

A thin web wrapper, a single screen, or content only a website could provide. Native navigation, offline and error states, and platform integration (notifications, Health, widgets, StoreKit) make the app an app. Review also checks that the app isn't merely a marketing or catalog site.

## 4.8 Login services

A third-party or social login (Google, Facebook, X, LinkedIn, Amazon, WeChat) used for the primary account requires an equivalent option that limits data to name and email, allows a private email, and doesn't track for ads. Sign in with Apple qualifies. Exceptions such as company-only accounts or enterprise/education logins are listed in the guideline.

## 5.1.1(i) Privacy policy

The link goes in the App Store Connect field and in the app, easy to find. The policy names what is collected, how, every use, every third party (including AI and analytics providers) and their equal protection, retention and deletion, and how to revoke consent. Apple reads the live URL: keep it deployed and update it before shipping a new data flow.

## 5.1.1(iv) Permission requests

Reviewer: a pre-permission button labelled "Allow X", a prompt at launch with no context, or access forced for an unrelated feature.

HIG (hig-privacy, "Pre-alert screens"): one button that opens the system alert, labelled "Continue" or "Next"; no cancel or skip on that screen unless it is a legal consent. Request at the moment the feature needs it. Offer an alternative when declined (for example, manual address entry instead of location).

Typical rejections: a pre-permission card titled "Allow <resource>", or a non-essential feature requesting location at launch (for example for a returning user on a new device). Fix: relabel to "Continue"; use the resource only if it is already granted, otherwise fall back silently and ask in context later.

## 5.1.1(v) Account deletion

- In-app, discoverable (usually Settings > Account), and it deletes the account and its data. Deactivating or signing out doesn't count; a "Delete" button that only signs out is worse than none.
- Confirmation steps are fine. A regulated industry may require extra steps; explain them in the notes.
- Sign in with Apple users: revoke their tokens through the REST API on deletion (tn3194-siwa-account-deletion, siwa-revoke-tokens).
- Server pattern: one server-side routine scoped to the caller (for example a security-definer SQL function keyed on the caller's auth ID, or an authenticated API route) that deletes the auth user and cascades. The client never holds an admin secret.
- Update the support page and FAQ with what deletion removes.

## 5.1.2(i) Sharing data with third parties, including AI providers

Reviewer: the app sends personal data to a third-party AI service without disclosure or permission. The guideline now names "third-party AI" explicitly.

Fix:
- An in-app consent screen before any data flows, onboarding included. It says what data (health metrics, messages, profile fields), who receives it (name the chain, e.g. your server → model router → model vendors), why, and links the privacy policy. Explicit Agree; a decline path that doesn't send anything.
- Persist consent with a versioned key and reset it on sign-out, so a new user consents for themselves.
- Update the privacy policy's third-party section and the App Privacy label (data shared with third parties).

## 5.1.3 Health data

HealthKit and other health data can't be used for advertising, marketing or data mining, and can't be shared without permission (5.1.3(i)). Don't write false data, and don't store personal health information in iCloud (5.1.3(ii)). Request only the types you use; declare `NSHealthUpdateUsageDescription` only if you write. The privacy policy must cover health data explicitly (healthkit-protecting-user-privacy).

## 5.6.1 Review prompts

Use the system review API (`SKStoreReviewController` / `requestReview`). Custom rating prompts are disallowed. Don't pre-filter users ("Do you like the app?" then sending only fans to the store) and don't incentivize reviews (5.6.3 discovery fraud).

## Reply templates

Write replies in English: short, factual, verifiable. One section per guideline.

```
Hello App Review team,

Thank you for reviewing <App> <version> (<build>).

Guideline <x.y.z> — <title>
We <what changed, one sentence>. To verify: <exact path, e.g. Settings > Account > Delete Account>.

Guideline <...>
...

Demo account: <user> / <password> (has an active subscription in the sandbox / no setup needed).
<If server-only:> This was a server-side issue and the fix is live; build <n> can be reviewed again without a new binary.

Best regards,
<name>
```

For "2.1 Information Needed" questions, number the answers to match the reviewer's numbered questions, one paragraph each.
