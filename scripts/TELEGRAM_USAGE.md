# Telegram notifications

Reused and extended from the existing Tikz Manager script. Windows PowerShell 5.1+, same Windows account as the DPAPI configuration. Config stays at LOCALAPPDATA/CodexTelegram/config.json; it is never copied into this workspace. No automatic retry. Failures warn and let the phase continue. Success requires API ok=true; message_id is reported when provided. Only numeric API/HTTP codes and sanitized timeout status may be logged.

```powershell
& ./scripts/notify-telegram.ps1 -Project 'LaTeX Question Studio' -Phase 'Phase 00' -Status testing -Summary 'B?o c?o ki?m tra'
& ./scripts/notify-telegram.ps1 -Project 'LaTeX Question Studio' -Phase 'Phase 00' -Status testing -ImagePath 'artifacts/Phase 00 preview.png' -Caption 'Thi?t k? minh h?a b?ng d? li?u m?u'
# Original bytes, without photo processing:
& ./scripts/notify-telegram.ps1 -Project 'LaTeX Question Studio' -Phase 'Phase 00' -Status testing -ImagePath 'artifacts/Phase 00 preview.png' -Caption '?nh nguy?n b?n' -AsDocument
& ./scripts/test_notify_telegram.ps1
```

Review images and metadata before sending. Never send tokens, passwords, personal data, configuration windows or full desktop captures. Phase 00 image is a synthetic concept mockup, not a running application or compiled LaTeX output. Mock regression passed. One real sendPhoto request was attempted, but did not return ok=true; delivery is unconfirmed. No automatic resend was made. No commit or push.
