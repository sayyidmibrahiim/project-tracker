---
inclusion: always
---

# Product: Project Tracker DBS

Windows desktop app untuk tracking DBS Change Request (CR) deployments.
Single-user, no cloud, no database server. Data ada di local filesystem.

## Business domain

- CR = Change Request (unit kerja deployment)
- Setiap CR punya sub-projects; masing-masing punya Drone Ticket + Drone State sendiri
- CR Number shared across all sub-projects; Drone state independent per sub-project
- CR State dan Drone State di-set manual secara independen (tidak otomatis dari folder state)
- Folder structure di Windows filesystem = state machine
- Folder transitions: UAT_PREPARE → PROD_READY → IMPLEMENTED / POSTPONED / CANCELED
- T-10 rule: CR pending approval ≤10 hari memblok transisi tertentu (bisa di-override manual)

## Deployment context

- Dev di Pop!\_OS Linux → transfer via zip/email ke Windows office laptop
- Windows laptop: HP EliteBook 835 G11, strict IT policy, install via JFrog repo internal
- Final packaging: PyInstaller → .exe standalone Windows
- Target user: deployment engineer DBS, pakai di laptop kantor sendiri
