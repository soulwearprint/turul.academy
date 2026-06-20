-- v3_harden_rls_auto_enable
-- Supabase project: tqsrwhvvghryycgsxfsj (Turul ACADEMY)
--
-- Security hardening: public.rls_auto_enable() is a SECURITY DEFINER event-trigger
-- function (auto-enables RLS on new public tables). Postgres grants EXECUTE to
-- PUBLIC by default, which also exposed it via the PostgREST RPC route
-- (/rest/v1/rpc/rls_auto_enable) to anon + authenticated — flagged as a
-- privilege-escalation risk by the Supabase advisor.
--
-- Event triggers fire via the system, NOT via the EXECUTE privilege, so revoking
-- these grants has zero functional impact on auto-RLS. Direct RPC calls now 401.

REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;

-- Result: EXECUTE remains only for postgres + service_role.
