# R1 Stage 1 Phase C v19.7.3 OAuth Operator Protocol

Status: DRAFT REVIEW ONLY / NO LIVE AUTHORITY

1. After the exact reviewed OAuth launch action is delivered and pasted once, the Git credential-helper prompt MUST visibly appear before device-code display.
2. The only permitted answer to that prompt is exactly `No`. Historical v4 `Yes` text is superseded and NONAUTHORITY.
3. If the expected prompt is absent, materially different, auto-skipped, already-helper/no-prompt, or the Owner accidentally answers anything other than `No`: STOP, delete Codespace, no retry.
4. When the one-time GitHub device code becomes visible, do not send Core/chat any screenshot, photo, screen recording, OCR, copied terminal output, transcription, code value, or code characters. The only permitted progress report is exactly `DEVICE_CODE_DISPLAYED_NO_CODE_SHARED`.
5. After Core performs a Fresh authority/binding check, the only permitted terminal/UI action at that boundary is one Enter keystroke to continue the already-running reviewed `gh auth login` device flow. No new shell command is permitted.
6. Complete authorization only in first-party GitHub UI. Do not enter GitHub username/password in terminal/text-browser.
7. After first-party GitHub reports successful device connection, the only permitted progress report is exactly `GITHUB_DEVICE_CONNECTED_NO_CODE_SHARED`.
8. Return to the dedicated Codespace. Do not run repository commands from the returned ordinary shell. Await/deliver only the exact reviewed post-OAuth reentry action.
9. Any device-code disclosure, unexpected prompt/output, session loss, accidental extra input, or uncertainty consumes the one-shot session: STOP/delete/no retry.

These acknowledgements are progress evidence only. They are not authentication, scope, or admin proof; the downstream exact technical gates remain mandatory.