<!-- source: https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview | fetched: 2026-10-05 -->
# TestFlight Overview

iOS macOS visionOS tvOS watchOS

TestFlight lets you distribute beta builds of your app, manage beta testers, and collect feedback. [Learn more.](https://developer.apple.com/testflight/)

Make improvements to your app and continue distributing builds until all issues are resolved before you [submit your app for review](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review).

To use [TestFlight for Mac](https://apps.apple.com/us/app/testflight/id899247664), build your macOS apps with Xcode 13 or later. If your app includes an App Clip, you can invite testers to [test the App Clip experience](https://developer.apple.com/help/app-store-connect/test-a-beta-version/test-an-app-clip-experience) on its own. Testers who are invited to test your app can test both the app and the App Clip. Either the app or the App Clip can be installed on a device at a time. Testers can choose to switch between them at any time.

[Learn how to manage beta testing using the App Store Connect API.](https://developer.apple.com/documentation/appstoreconnectapi/prerelease_versions_and_beta_testers)

## Step 1: Provide test information

[Provide test information](https://developer.apple.com/help/app-store-connect/test-a-beta-version/provide-test-information) about your app, such as a beta app description, an explanation of features to test, and an email address where feedback can be submitted. You can also choose to show approved app screenshots and your app category.

### Step 2: Upload your build or assets

[Upload your build to App Store Connect.](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds) Read Cryptography and US export compliance to determine if you need to [provide app encryption documentation](https://developer.apple.com/help/app-store-connect/manage-app-information/overview-of-export-compliance) for your app. You can test a build for up to 90 days.

**Note:** For builds to be eligible for TestFlight, they must include application identifiers within the provisioning profiles.

You also have the option to upload assets that are managed separately from a build by using [Apple-Hosted Background Assets](https://developer.apple.com/help/app-store-connect/manage-asset-packs/overview-of-apple-hosted-asset-packs).

### Step 3: Invite internal and external testers

[Create groups](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers#create-a-group) for testers, then assign specific builds to them. After you've added builds to a group, you can add [external testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers) (up to 10,000 people) and [internal testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers) (up to 100 App Store Connect users with access to your content) to test your app. If you invite external testers, your beta build may require review. When you add the first build of your app to a group, the build gets sent to App Review to make sure it follows the [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/). A review is required only for the first build. Subsequent builds may not require a full review. Testing can begin once a build is approved.

**Note:** [Managed Apple Accounts](https://support.apple.com/HT210737) created in reserved domains can’t be used to test builds. Learn more about reserved domains in [Apple School Manager](https://support.apple.com/guide/apple-school-manager/add-and-verify-a-domain-axm48c3280c0/web) or [Apple Business](https://supportb.corp.apple.com/guide/business/welcome/web).

### Step 4: Testers download TestFlight and accept your invitations

Testers install the free TestFlight app on their devices. Then they use their invitation email or a public link to accept invitations, install your app, send feedback, and get updates. Testers download and install thinned variants of your app.

**Note:** Setting specific criteria for your public link invitations can limit the number of external testers who can test your app.

### Step 5: View tester and build information

Track tester engagement and your app's performance by [viewing build status and metrics](https://developer.apple.com/help/app-store-connect/test-a-beta-version/view-build-status-and-metrics). These metrics include the number of sessions and crashes. Also, you can resend email invitations to testers who haven't accepted their invitation.

### Step 6: Collect feedback from testers

Testers using TestFlight version 2.3 or later on iOS, macOS, and visionOS can submit feedback either through the TestFlight app or by taking a screenshot directly within your beta app. You can view this [tester feedback](https://developer.apple.com/help/app-store-connect/test-a-beta-version/view-tester-feedback) in the TestFlight Feedback section in App Store Connect. Testers running tvOS or earlier versions of iOS can send feedback to the email address you specified in step 1.

### Step 7: Stop testing

When testing is complete, you have the option to [expire a build](https://developer.apple.com/help/app-store-connect/test-a-beta-version/stop-testing-a-build) to stop testing it. If you don’t expire your build and [submit it to the App Store](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/overview-of-publishing-your-app-on-the-app-store), testers who received an invitation to test will still be able to test your build even after it goes live on the App Store. Your build becomes unavailable for testers after 90 days.

**Related** [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds) [Overview of publishing your app on the App Store](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/overview-of-publishing-your-app-on-the-app-store) [Overview of submitting for review](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/overview-of-submitting-for-review) [Get started with TestFlight](https://developer.apple.com/videos/play/tech-talks/110343/)
