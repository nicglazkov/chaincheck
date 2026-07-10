# Security policy

ChainCheck stores no accounts and no personal data. The only stored values are
anonymous FCM device tokens paired with watched route ids. Still, if you find
a vulnerability, I want to hear about it.

## Reporting

Please report privately through GitHub: use the **Report a vulnerability**
button under the repository's Security tab. If that does not work for you,
email nic@glazkov.com.

Please do not open a public issue for a security problem.

## Scope

- The API at chaincheck-api-*.run.app and everything under `backend/`
- The Android app under `composeApp/`

Out of scope: the upstream public data feeds (Caltrans, CHP, NWS, Open-Meteo,
resort sites) belong to their operators, not this project.
