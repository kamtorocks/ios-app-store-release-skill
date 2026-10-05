<!-- source: https://developer.apple.com/documentation/appstoreservernotifications/enabling-app-store-server-notifications | fetched: 2026-10-05 -->
# Enabling App Store Server Notifications

> Article

Configure your server and provide an HTTPS URL to receive notifications about in-app purchase events and unreported external purchase tokens.

## Overview

[App Store Server Notifications](https://developer.apple.com/documentation/appstoreservernotifications) is a server-to-server service that sends real-time notifications for in-app purchase events, and notifications for unreported external purchase tokens. To enable notifications, set up an HTTPS URL on your server, and configure settings in App Store Connect.

For information about parsing and interpreting notifications, see [Receiving App Store Server Notifications](https://developer.apple.com/documentation/appstoreservernotifications/receiving-app-store-server-notifications).

### Set up your server and App Store Connect settings

To receive server notifications from the App Store, your server must support the Transport Layer Security (TLS) 1.2 protocol or later.

To enable App Store Server Notifications, follow these steps:

1. Determine the HTTPS URL on your server to receive notifications for the production environment.
2. Optionally, determine the HTTPS URL on your server to receive notifications for the sandbox environment for testing notifications. You may use the same URL for both the production and the sandbox environments.
3. App Store Connect gives you the choice of receiving version 2 or version 1 notifications for each environment. To choose version 2, set up your endpoint as [App Store Server Notifications V2](https://developer.apple.com/documentation/appstoreservernotifications/app-store-server-notifications-v2).
4. Configure your URL in App Store Connect. For more information, see [Enter a URL for App Store Server Notifications](https://help.apple.com/app-store-connect/#/dev0067a330b).

> **Important:**  If you specify a port in your URL, the port must be either `443` or greater than or equal to `1024`. For example, the URL `https://example.com:1234/notifications` specifies the port `1234`.

Configure your server to respond with HTTP status codes to indicate whether the App Store server notification `POST` is successful. For more information, see [Responding to App Store Server Notifications](https://developer.apple.com/documentation/appstoreservernotifications/responding-to-app-store-server-notifications).

For new implementations, use [App Store Server Notifications V2](https://developer.apple.com/documentation/appstoreservernotifications/app-store-server-notifications-v2). To transition from using version 1 notifications to version 2, test version 2 notifications in the sandbox environment before you update your production environment to version 2.

For information about changes to App Store Server Notifications, see [App Store Server Notifications changelog](https://developer.apple.com/documentation/appstoreservernotifications/app-store-server-notifications-changelog).

### Configure an allow list

If your server requires IP addresses to be on an allow list, add the IP address subnet `17.0.0.0/8` to allow your server to receive notifications from the App Store server. This subnet applies to both the sandbox and the production environments.

### Test your server setup

To determine whether your server is receiving notifications, call the [Request a Test Notification](https://developer.apple.com/documentation/appstoreserverapi/request-a-test-notification) endpoint in the [App Store Server API](https://developer.apple.com/documentation/appstoreserverapi). This endpoint asks the App Store server to send a notification with the [notificationType](https://developer.apple.com/documentation/appstoreservernotifications/notificationtype) `TEST`. Use the [testNotificationToken](https://developer.apple.com/documentation/appstoreserverapi/testnotificationtoken) you receive to call the [Get Test Notification Status](https://developer.apple.com/documentation/appstoreserverapi/get-test-notification-status) endpoint to learn how your server responds to the test notification.

The App Store server sends the `TEST` notification in the version 2 notification format. However, it sends it to your server regardless of whether you configure a version 1 or version 2 notification URL in App Store Connect.

## See Also

### Essentials

- [Receiving App Store Server Notifications](https://developer.apple.com/documentation/appstoreservernotifications/receiving-app-store-server-notifications) — Implement server-side code to receive and parse notification posts.
- [Responding to App Store Server Notifications](https://developer.apple.com/documentation/appstoreservernotifications/responding-to-app-store-server-notifications) — Send HTTP status codes to indicate the success of a notification post.
- [App Store Server Notifications changelog](https://developer.apple.com/documentation/appstoreservernotifications/app-store-server-notifications-changelog) — Learn about changes to the App Store Server Notifications service.
