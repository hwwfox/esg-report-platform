-- V001 Auth + Tenant + RBAC: set deterministic demo password hashes for seeded users.
-- Demo password for all seeded users: ChangeMe123!
BEGIN;
SET search_path TO esg, public;

UPDATE users
SET password_hash = 'pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$TYS3ovZYqJ2bTLGKaJj2isqd+keujkLbW75Xrp0lJf8='
WHERE email IN (
  'admin@example.com',
  'project.owner@example.com',
  'esg.expert@example.com',
  'ehs.collector@example.com',
  'ehs.reviewer@example.com',
  'hr.collector@example.com',
  'hr.reviewer@example.com'
);

COMMIT;
