# Notification preferences (iOS)

You just set up a new iPhone. Before you finish, take a minute to see how **notifications** work on this phone.

1. `launch` **Settings** (`com.apple.Preferences`).
2. Tap the **search** field at the top, `type_text` **Notifications**, then tap the **Notifications** row (not the Apps list).
3. Open **one app** you use (Mail, Messages, Safari, etc.) and review its notification options.
4. Decide whether you'd **keep notifications on** for that app on a phone you use every day.

Hand in your decision as JSON:

```json
{
  "keep_notifications_on": true,
  "app_reviewed": "<app name you looked at>",
  "reason": "<why, in your own words>"
}
```

`keep_notifications_on` must be `true` or `false`. Don't change unrelated system settings.

When you are ready to submit, call the **done** tool with `success: true` and put that JSON (as a single-line string) in the `message` field. Do not keep navigating after you have your answer.
