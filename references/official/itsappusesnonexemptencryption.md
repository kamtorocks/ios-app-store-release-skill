<!-- source: https://developer.apple.com/documentation/bundleresources/information-property-list/itsappusesnonexemptencryption | fetched: 2026-10-05 -->
# ITSAppUsesNonExemptEncryption

> Property List Key · macOS 10.0+

A Boolean value indicating whether the app uses encryption.

## Details

- Key: `ITSAppUsesNonExemptEncryption` (Xcode: App Uses Non-Exempt Encryption)
- Type: boolean

## Discussion

Set the value for this key to `NO` in your app’s [Information Property List](https://developer.apple.com/documentation/bundleresources/information-property-list) file to indicate that your app—including any third-party libraries you link against—either uses no encryption, or only uses encryption that’s exempt from export compliance requirements, as described in [Overview of export compliance](https://developer.apple.com/help/app-store-connect/manage-app-information/overview-of-export-compliance/). Set the value to `YES` to indicate that your app uses non-exempt encryption.

If you set the value to `YES`, you typically also provide a value for the [ITSEncryptionExportComplianceCode](https://developer.apple.com/documentation/bundleresources/information-property-list/itsencryptionexportcompliancecode) key. You set that key’s value using a code Apple provides after successfully reviewing your export compliance documentation.

If you don’t have the [ITSAppUsesNonExemptEncryption](https://developer.apple.com/documentation/bundleresources/information-property-list/itsappusesnonexemptencryption) key in your app’s `Info.plist` file, App Store Connect walks you through an export compliance questionnaire every time you upload a new version of your app. Including the key streamlines the app submission process.

For additional information, see [Complying with Encryption Export Regulations](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations).

## See Also

### Security

- [NSUpdateSecurityPolicy](https://developer.apple.com/documentation/bundleresources/information-property-list/nsupdatesecuritypolicy) — A dictionary that identifies which apps or installer packages the operating system allows to write to the app’s bundle.
- [NSAppBundlesUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsappbundlesusagedescription) — A message that tells people why the app needs to access the contents of other apps’ bundles.
- [NSAppDataUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsappdatausagedescription) — A message that tells people why the app needs to access files in other apps’ sandbox containers.
- [NSUserTrackingUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsusertrackingusagedescription) — A message that explains the purpose for accessing data that an app can use to track a person or device.
- [NSUserTrackingMarkdownUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsusertrackingmarkdownusagedescription) — A message that explains the purpose for accessing data that an application can use to track a person or device.
- [NSAppleEventsUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nsappleeventsusagedescription) — A message that tells people why the app is requesting the ability to send Apple events.
- [NSSystemAdministrationUsageDescription](https://developer.apple.com/documentation/bundleresources/information-property-list/nssystemadministrationusagedescription) — A message in macOS that tells people why the app is requesting to manipulate the system configuration.
- [ITSEncryptionExportComplianceCode](https://developer.apple.com/documentation/bundleresources/information-property-list/itsencryptionexportcompliancecode) — The export compliance code provided by App Store Connect for apps that require it.
