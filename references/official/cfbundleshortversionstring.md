<!-- source: https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleshortversionstring | fetched: 2026-10-05 -->
# CFBundleShortVersionString

> Property List Key · iOS 2.0+, iPadOS 2.0+, macOS 10.0+, tvOS 9.0+, visionOS 1.0+, watchOS 2.0+

The release or version number of the bundle.

## Details

- Key: `CFBundleShortVersionString` (Xcode: Bundle version string (short))
- Type: string

## Discussion

This key is a user-visible string for the version of the bundle. The required format is three period-separated integers, such as 10.14.1. The string can only contain numeric characters (0-9) and periods.

Each integer provides information about the release in the format [*Major*].[*Minor*].[*Patch*]:

- Major: A major revision number.
- Minor: A minor revision number.
- Patch: A maintenance release number.

This key is used throughout the system to identify the version of the bundle.

## See Also

### Bundle version

- [CFBundleVersion](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion) — The version of the build that identifies an iteration of the bundle.
- [CFBundleInfoDictionaryVersion](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleinfodictionaryversion) — The current version of the Information Property List structure.
- [NSHumanReadableCopyright](https://developer.apple.com/documentation/bundleresources/information-property-list/nshumanreadablecopyright) — A human-readable copyright notice for the bundle.
