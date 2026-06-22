-- V001 Auth + Tenant + RBAC: set deterministic demo password hashes for seeded users.
-- Demo password for DEFAULT tenant seeded users only: ChangeMe123!
BEGIN;
SET search_path TO esg, public;

UPDATE users AS u
SET password_hash = 'pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$TYS3ovZYqJ2bTLGKaJj2isqd+keujkLbW75Xrp0lJf8='
FROM tenants AS t
WHERE u.tenant_id = t.tenant_id
  AND t.tenant_code = 'DEFAULT'
  AND (u.password_hash IS NULL OR u.password_hash = '')
  AND u.email IN (
    'admin@example.com',
    'project.owner@example.com',
    'esg.expert@example.com',
    'ehs.collector@example.com',
    'ehs.reviewer@example.com',
    'hr.collector@example.com',
    'hr.reviewer@example.com'
  );

COMMIT;
