# In-app purchase and subscriptions

Archived docs: storekit-sandbox, asn-v2-enabling, submit-an-in-app-purchase, auto-renewable-subscriptions. Guidelines: 2.1(b), 3.1.1, 3.1.2.

## Contents

- Preconditions: why products don't load
- App Review buys in the sandbox against your production backend
- Server verification rules
- Client rules
- Paywall disclosure checklist
- Submitting IAP for review
- Identity pitfalls

## Preconditions: why products don't load

Check these before debugging code:
- Business: the Paid Apps Agreement is active and banking and tax are complete. Until then, products don't load in the sandbox either.
- Product: the ID matches exactly; the product has a localization, price and review screenshot, and is Ready to Submit; subscriptions sit in a Subscription Group.
- First submission: the first IAP of each type goes for review together with an app version (submit-an-in-app-purchase).
- Identity: the running build's bundle ID owns the products. Flavor apps with another bundle ID can't see production products.
- Xcode: a StoreKit Configuration file selected in the scheme replaces the real store during Xcode runs. Unset it to test the sandbox.
- Propagation: new or edited products can take a while to appear.

## App Review buys in the sandbox against your production backend

Reviewers and TestFlight testers make purchases in the sandbox environment, using your production-signed build and your production server. A server that assumes "production build means production transactions" fails exactly during review.
- StoreKit 2 / App Store Server API: read `environment` from the signed transaction and verify against the matching environment.
- Legacy `verifyReceipt`: verify against production first; on status 21007 ("sandbox receipt sent to production"), retry against the sandbox.
- Tag each entitlement with its environment. Don't let a sandbox transaction overwrite a production entitlement (a production-precedence guard), and test the sandbox with separate accounts.
- App Store Server Notifications V2: set both the production and the sandbox URL in App Store Connect (asn-v2-enabling).

## Server verification rules

1. Verify the JWS signature chain, then check bundle ID, product ID, environment and revocation. Record purchases idempotently by `transactionId`, linking renewals by `originalTransactionId`.
2. Record lapsed transactions; don't reject them. StoreKit re-delivers old and renewed transactions, and sandbox periods last minutes, so a valid purchase can arrive already expired. Grant access when reading the entitlement (expiry in the future and an active status). Failure mode: rejecting `expiresDate <= now` at verify time shows the reviewer "This subscription has expired", a 2.1(b) rejection. It is a server-only fix; the same build can be re-reviewed.
3. Transactions for another account (an `originalTransactionId` already bound to a different user): choose a policy (move on restore, or reject with a clear message) and implement it explicitly. `appAccountToken` binds a purchase to your user ID.
4. Infrastructure errors while reading entitlements shouldn't silently degrade users to free or upgrade them to paid. Fail visibly, log the reason, and let the caller's fallback decide.

## Client rules

- Show success only after a server-verified grant. Closing the paywall or showing "Welcome" on an optimistic local grant hides real failures. Failure mode: the reviewer taps subscribe, the sheet closes, and the account is still free.
- Make every failure path visible: store unavailable, product not loaded, purchase error, server rejection mapped to a reason (revoked, sandbox/production mismatch, product not configured), network failure. A button that does nothing is a 2.1(b) rejection.
- A subscription the user already owns can come back from StoreKit with no payment sheet. Handle it like a restore.
- Finish the transaction only after the server has recorded it; otherwise purchases loop or are lost.
- Put Restore Purchases in the purchase flow and in Settings. Show Manage Subscription (`showManageSubscriptions`, or `https://apps.apple.com/account/subscriptions`) while a subscription is active.
- Hide every purchase surface behind one flag until the full chain works in the sandbox. Reviewers try everything they can see.
- A web or browser checkout is for web visitors only. Inside the app, all unlocking goes through IAP (3.1.1).

## Paywall disclosure checklist

Per 3.1.2(c) and Schedule 2 of the Developer Program License Agreement; read the live text before relying on wording:
- Subscription name, period, price per period, and what the user gets.
- The amount that will be billed regularly is the most prominent price.
- Introductory offer or free trial: secondary but always visible, worded the way StoreKit will charge (for example "$4.99 for the first month, then $19.99/month"). Eligibility comes from StoreKit (`isEligibleForIntroOffer`); don't promise it to ineligible users and don't hide it behind your own time window.
- A statement that the subscription auto-renews, and how to cancel.
- Working Terms of Use (EULA) and Privacy Policy links inside the flow, plus Restore.
- No countdowns or scarcity that aren't real (3.1.2(a): tricking users "under false pretenses").
- Prices are the localized strings from StoreKit, never hardcoded.
- Metadata: Privacy Policy URL field, and a Terms of Use link in the description or a custom EULA.

## Submitting IAP for review

- Each product has a review screenshot (the paywall) and review notes.
- App Review Notes say how to reach the paywall, that purchases are sandbox, which demo account to use, and what the subscription delivers (if it unlocks a service such as coaching or AI, say what the reviewer will see after buying).
- If a configured product can't be reached in the app, explain why or remove it from the submission (2.1(b)).
- A product priced far above the others can trigger an automated "confirm the intended price" hold (rejection-playbook.md, guideline 3). Say in Review Notes that the price is intended and why.

## Identity pitfalls

- Sign in with Apple can create a second auth user for the same person (Hide My Email, or the same person on another provider). Allowlists, comp grants and manual entitlements keyed by user ID must cover every identity.
- Decide what happens when one Apple ID buys in two app accounts (restore moves the entitlement, or it's refused), and tell the user what happened.
