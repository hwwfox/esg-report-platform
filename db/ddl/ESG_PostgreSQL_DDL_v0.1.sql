-- ESG报告软件 PostgreSQL DDL 初版 v0.1
-- 目标：覆盖MVP P0主链路：多租户、企业、项目、组织架构、标准库、同行报告解析、
-- 推荐、采集审核、ESG数据表、知识库、AI写作、来源引用、校对、导出、日志。
-- 数据库：PostgreSQL 14+
-- 建议：PoC/演示环境可直接使用；生产环境需结合迁移工具 Flyway / Liquibase / Alembic 管理。

CREATE SCHEMA IF NOT EXISTS esg;
SET search_path TO esg, public;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- 1. 通用函数
-- =========================================================

CREATE OR REPLACE FUNCTION esg.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- 2. 枚举类型
-- =========================================================

DO $$ BEGIN
  CREATE TYPE tenant_status AS ENUM ('active', 'inactive');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE user_status AS ENUM ('active', 'inactive', 'invited');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE project_status AS ENUM (
    'draft',
    'peer_analysis',
    'topic_confirmation',
    'task_assignment',
    'data_collection',
    'department_review',
    'writing',
    'chapter_review',
    'full_review',
    'export_ready',
    'completed',
    'archived'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE status_active AS ENUM ('draft', 'active', 'inactive');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE esg_category AS ENUM ('E', 'S', 'G');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE materiality_level AS ENUM ('high', 'medium', 'low', 'unknown', 'not_applicable');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE metric_type AS ENUM ('quantitative', 'qualitative');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE data_type AS ENUM ('number', 'text', 'percentage', 'currency', 'boolean', 'date');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE parse_status AS ENUM (
    'uploaded',
    'pending',
    'parsing',
    'ai_reviewing',
    'pending_human_review',
    'approved',
    'stored',
    'failed',
    'rejected'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('pending', 'running', 'succeeded', 'failed', 'retrying', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE task_status AS ENUM ('pending', 'draft', 'submitted', 'under_review', 'returned', 'approved', 'not_applicable');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE review_status AS ENUM ('pending', 'accepted', 'edited', 'rejected', 'ignored', 'confirmed', 'approved', 'returned');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE ai_call_status AS ENUM ('success', 'failed', 'timeout', 'invalid_output', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE severity_level AS ENUM ('high', 'medium', 'low', 'info');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE source_type AS ENUM (
    'peer_report',
    'standard_clause',
    'esg_data',
    'knowledge_document',
    'interview',
    'user_input',
    'system_calculation',
    'ai_generated',
    'task_submission',
    'file',
    'review'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE support_status AS ENUM ('fully_supported', 'partially_supported', 'unsupported', 'contradicted', 'source_missing');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =========================================================
-- 3. 租户、企业、用户、权限
-- =========================================================

CREATE TABLE IF NOT EXISTS tenants (
  tenant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_code varchar(64) UNIQUE NOT NULL,
  tenant_name varchar(255) NOT NULL,
  status tenant_status NOT NULL DEFAULT 'active',
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS enterprises (
  enterprise_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_code varchar(64),
  enterprise_name varchar(255) NOT NULL,
  enterprise_short_name varchar(128),
  stock_code varchar(64),
  exchange varchar(64),
  country_or_region varchar(64),
  industry_description text,
  main_business text,
  status tenant_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, enterprise_code),
  UNIQUE (tenant_id, enterprise_name)
);

CREATE TABLE IF NOT EXISTS users (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  name varchar(128) NOT NULL,
  email varchar(255) NOT NULL,
  phone varchar(64),
  avatar_url text,
  password_hash text,
  status user_status NOT NULL DEFAULT 'active',
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS roles (
  role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  role_code varchar(64) NOT NULL,
  role_name varchar(128) NOT NULL,
  role_description text,
  permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_system_role boolean NOT NULL DEFAULT false,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, role_code)
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  user_id uuid NOT NULL REFERENCES users(user_id),
  role_id uuid NOT NULL REFERENCES roles(role_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid,
  org_unit_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, role_id, enterprise_id, project_id, org_unit_id)
);

CREATE TABLE IF NOT EXISTS enterprise_user_access (
  access_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  user_id uuid NOT NULL REFERENCES users(user_id),
  access_scope varchar(64) NOT NULL DEFAULT 'all',
  org_unit_ids uuid[] DEFAULT '{}',
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (enterprise_id, user_id)
);

-- =========================================================
-- 4. GICS行业与企业行业历史
-- =========================================================

CREATE TABLE IF NOT EXISTS gics_industries (
  gics_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  gics_code varchar(32) NOT NULL UNIQUE,
  gics_name_en varchar(255) NOT NULL,
  gics_name_cn varchar(255),
  gics_level smallint NOT NULL CHECK (gics_level BETWEEN 1 AND 4),
  parent_gics_code varchar(32),
  status status_active NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS enterprise_gics_history (
  history_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  gics_level smallint NOT NULL CHECK (gics_level BETWEEN 1 AND 4),
  gics_code varchar(32) NOT NULL REFERENCES gics_industries(gics_code),
  confidence numeric(5,4),
  source varchar(64) NOT NULL DEFAULT 'manual',
  reason text,
  confirmed_by uuid REFERENCES users(user_id),
  confirmed_at timestamptz,
  is_current boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 5. 报告项目与成员
-- =========================================================

CREATE TABLE IF NOT EXISTS report_projects (
  project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  project_name varchar(255) NOT NULL,
  report_year integer NOT NULL,
  report_type varchar(64) NOT NULL DEFAULT 'ESG',
  report_language varchar(32) NOT NULL DEFAULT 'zh',
  reporting_period_start date,
  reporting_period_end date,
  report_boundary text,
  project_owner_user_id uuid REFERENCES users(user_id),
  project_status project_status NOT NULL DEFAULT 'draft',
  selected_standard_codes text[] NOT NULL DEFAULT '{}',
  locked_at timestamptz,
  completed_at timestamptz,
  archived_at timestamptz,
  created_by uuid REFERENCES users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, enterprise_id, report_year, project_name)
);

CREATE TABLE IF NOT EXISTS project_members (
  project_member_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  user_id uuid NOT NULL REFERENCES users(user_id),
  project_role varchar(64) NOT NULL,
  org_unit_id uuid,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, user_id, project_role, org_unit_id)
);

-- =========================================================
-- 6. 组织架构
-- =========================================================

CREATE TABLE IF NOT EXISTS org_units (
  org_unit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  parent_org_unit_id uuid REFERENCES org_units(org_unit_id),
  org_unit_code varchar(64),
  org_unit_name varchar(255) NOT NULL,
  org_unit_type varchar(64) NOT NULL,
  department_owner_user_id uuid REFERENCES users(user_id),
  sort_order integer NOT NULL DEFAULT 0,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (enterprise_id, org_unit_code)
);

CREATE TABLE IF NOT EXISTS org_unit_users (
  org_unit_user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  org_unit_id uuid NOT NULL REFERENCES org_units(org_unit_id),
  user_id uuid NOT NULL REFERENCES users(user_id),
  assignment_role varchar(64) NOT NULL, -- collector / reviewer / owner / member
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_unit_id, user_id, assignment_role)
);

CREATE TABLE IF NOT EXISTS project_org_units (
  project_org_unit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  source_org_unit_id uuid REFERENCES org_units(org_unit_id),
  parent_project_org_unit_id uuid REFERENCES project_org_units(project_org_unit_id),
  org_unit_name varchar(255) NOT NULL,
  org_unit_type varchar(64) NOT NULL,
  collector_user_ids uuid[] NOT NULL DEFAULT '{}',
  reviewer_user_ids uuid[] NOT NULL DEFAULT '{}',
  snapshot_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 7. ESG标准、议题、指标基础库
-- =========================================================

CREATE TABLE IF NOT EXISTS esg_standards (
  standard_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  standard_code varchar(128) NOT NULL UNIQUE,
  standard_name varchar(255) NOT NULL,
  standard_short_name varchar(128),
  standard_type varchar(64) NOT NULL,
  applicable_market varchar(128),
  issuing_body varchar(255),
  description text,
  scope_type varchar(64) NOT NULL DEFAULT 'platform_public',
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS standard_versions (
  standard_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  standard_id uuid NOT NULL REFERENCES esg_standards(standard_id),
  standard_version_code varchar(128) NOT NULL UNIQUE,
  version_name varchar(128) NOT NULL,
  version_no varchar(64) NOT NULL,
  effective_date date,
  expired_date date,
  is_current boolean NOT NULL DEFAULT false,
  source_file_id uuid,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS standard_clauses (
  clause_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  standard_version_id uuid NOT NULL REFERENCES standard_versions(standard_version_id),
  clause_code varchar(128) NOT NULL UNIQUE,
  clause_no varchar(128) NOT NULL,
  clause_title varchar(255) NOT NULL,
  parent_clause_code varchar(128),
  clause_level smallint NOT NULL DEFAULT 1,
  clause_text text NOT NULL,
  clause_summary text,
  disclosure_type varchar(64) NOT NULL DEFAULT 'mixed',
  is_required varchar(32) NOT NULL DEFAULT 'conditional',
  applicable_condition text,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS esg_topics (
  topic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  topic_code varchar(128) NOT NULL UNIQUE,
  topic_name varchar(255) NOT NULL,
  topic_category esg_category NOT NULL,
  topic_description text,
  default_financial_materiality materiality_level DEFAULT 'unknown',
  default_impact_materiality materiality_level DEFAULT 'unknown',
  common_disclosure text,
  default_owner_department varchar(255),
  is_common boolean NOT NULL DEFAULT true,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS esg_metrics (
  metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  metric_code varchar(128) NOT NULL UNIQUE,
  metric_name varchar(255) NOT NULL,
  metric_type metric_type NOT NULL,
  data_type data_type NOT NULL,
  default_unit varchar(64),
  reporting_frequency varchar(64) DEFAULT 'annual',
  is_reusable boolean NOT NULL DEFAULT true,
  metric_description text,
  filling_instruction text,
  calculation_method text,
  evidence_requirement_text text,
  default_required boolean NOT NULL DEFAULT false,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS standard_topic_maps (
  map_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  standard_version_id uuid NOT NULL REFERENCES standard_versions(standard_version_id),
  topic_id uuid NOT NULL REFERENCES esg_topics(topic_id),
  related_clause_codes text[] NOT NULL DEFAULT '{}',
  is_key_topic boolean NOT NULL DEFAULT false,
  applicability_note text,
  status status_active NOT NULL DEFAULT 'active',
  UNIQUE (standard_version_id, topic_id)
);

CREATE TABLE IF NOT EXISTS topic_metric_maps (
  map_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id uuid NOT NULL REFERENCES esg_topics(topic_id),
  metric_id uuid NOT NULL REFERENCES esg_metrics(metric_id),
  default_selected boolean NOT NULL DEFAULT true,
  is_required boolean NOT NULL DEFAULT false,
  sort_order integer NOT NULL DEFAULT 0,
  recommended_collector_role varchar(128),
  recommended_reviewer_role varchar(128),
  status status_active NOT NULL DEFAULT 'active',
  UNIQUE (topic_id, metric_id)
);

CREATE TABLE IF NOT EXISTS clause_metric_maps (
  map_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clause_id uuid NOT NULL REFERENCES standard_clauses(clause_id),
  metric_id uuid NOT NULL REFERENCES esg_metrics(metric_id),
  disclosure_requirement_type varchar(64) NOT NULL DEFAULT 'conditional',
  standard_specific_instruction text,
  source_required boolean NOT NULL DEFAULT true,
  status status_active NOT NULL DEFAULT 'active',
  UNIQUE (clause_id, metric_id)
);

CREATE TABLE IF NOT EXISTS metric_validation_rules (
  validation_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_id uuid NOT NULL REFERENCES esg_metrics(metric_id),
  validation_rule_code varchar(128) NOT NULL UNIQUE,
  rule_type varchar(64) NOT NULL,
  rule_name varchar(255) NOT NULL,
  rule_params jsonb NOT NULL DEFAULT '{}'::jsonb,
  severity severity_level NOT NULL DEFAULT 'medium',
  block_submission boolean NOT NULL DEFAULT false,
  message text NOT NULL,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence_requirements (
  evidence_requirement_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  target_type varchar(64) NOT NULL, -- topic / metric
  target_code varchar(128) NOT NULL,
  evidence_type varchar(64) NOT NULL,
  evidence_name varchar(255) NOT NULL,
  is_required boolean NOT NULL DEFAULT false,
  file_format text[] NOT NULL DEFAULT '{}',
  description text,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS topic_aliases (
  topic_alias_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id uuid NOT NULL REFERENCES esg_topics(topic_id),
  alias_name varchar(255) NOT NULL,
  language varchar(32) NOT NULL DEFAULT 'zh',
  source_type varchar(64),
  match_priority varchar(32) DEFAULT 'medium',
  status status_active NOT NULL DEFAULT 'active',
  UNIQUE (topic_id, alias_name, language)
);

CREATE TABLE IF NOT EXISTS metric_aliases (
  metric_alias_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_id uuid NOT NULL REFERENCES esg_metrics(metric_id),
  alias_name varchar(255) NOT NULL,
  language varchar(32) NOT NULL DEFAULT 'zh',
  source_type varchar(64),
  match_priority varchar(32) DEFAULT 'medium',
  status status_active NOT NULL DEFAULT 'active',
  UNIQUE (metric_id, alias_name, language)
);

CREATE TABLE IF NOT EXISTS owner_rules (
  owner_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  target_type varchar(64) NOT NULL,
  target_code varchar(128) NOT NULL,
  recommended_owner_department varchar(255) NOT NULL,
  recommended_collaborator_departments text[] NOT NULL DEFAULT '{}',
  recommended_collector_role varchar(128),
  recommended_reviewer_role varchar(128),
  recommendation_reason text,
  status status_active NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS industry_applicability (
  applicability_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  target_type varchar(64) NOT NULL,
  target_code varchar(128) NOT NULL,
  gics_level smallint NOT NULL CHECK (gics_level BETWEEN 1 AND 4),
  gics_code varchar(32) NOT NULL,
  applicability_level varchar(32) NOT NULL DEFAULT 'medium',
  description text,
  status status_active NOT NULL DEFAULT 'active'
);

-- =========================================================
-- 8. 项目标准、议题、指标快照
-- =========================================================

CREATE TABLE IF NOT EXISTS project_standards (
  project_standard_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  standard_id uuid NOT NULL REFERENCES esg_standards(standard_id),
  standard_version_id uuid REFERENCES standard_versions(standard_version_id),
  standard_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  source varchar(64) NOT NULL DEFAULT 'manual',
  selected boolean NOT NULL DEFAULT true,
  confirmed_by uuid REFERENCES users(user_id),
  confirmed_at timestamptz,
  UNIQUE (project_id, standard_id)
);

CREATE TABLE IF NOT EXISTS project_topics (
  project_topic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  topic_id uuid REFERENCES esg_topics(topic_id),
  topic_code varchar(128) NOT NULL,
  topic_name varchar(255) NOT NULL,
  topic_category esg_category NOT NULL,
  source varchar(64) NOT NULL DEFAULT 'manual',
  adoption_rate numeric(6,4),
  financial_materiality materiality_level DEFAULT 'unknown',
  impact_materiality materiality_level DEFAULT 'unknown',
  priority varchar(32) DEFAULT 'medium',
  status status_active NOT NULL DEFAULT 'draft',
  selected boolean NOT NULL DEFAULT true,
  locked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, topic_code)
);

CREATE TABLE IF NOT EXISTS project_topic_metrics (
  project_topic_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  project_topic_id uuid NOT NULL REFERENCES project_topics(project_topic_id),
  metric_id uuid REFERENCES esg_metrics(metric_id),
  metric_code varchar(128) NOT NULL,
  metric_name varchar(255) NOT NULL,
  metric_type metric_type NOT NULL,
  data_type data_type NOT NULL,
  unit varchar(64),
  is_required boolean NOT NULL DEFAULT false,
  custom_filling_instruction text,
  metric_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  status status_active NOT NULL DEFAULT 'active',
  UNIQUE (project_topic_id, metric_code)
);

-- =========================================================
-- 9. 同行公司与同行报告
-- =========================================================

CREATE TABLE IF NOT EXISTS peer_company_profiles (
  peer_company_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name varchar(255) NOT NULL,
  company_short_name varchar(128),
  stock_code varchar(64),
  exchange varchar(64),
  gics_level_4_code varchar(32),
  gics_level_4_name varchar(255),
  main_business text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (stock_code, exchange)
);

CREATE TABLE IF NOT EXISTS project_peer_companies (
  project_peer_company_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  peer_company_id uuid NOT NULL REFERENCES peer_company_profiles(peer_company_id),
  business_similarity_score numeric(6,4),
  industry_leader_score numeric(6,4),
  report_availability_score numeric(6,4),
  overall_score numeric(6,4),
  recommendation_reason text,
  latest_report_year integer,
  has_report_in_library boolean NOT NULL DEFAULT false,
  selected boolean NOT NULL DEFAULT false,
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, peer_company_id)
);

CREATE TABLE IF NOT EXISTS file_objects (
  file_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  file_name varchar(512) NOT NULL,
  file_type varchar(64),
  file_size bigint,
  mime_type varchar(128),
  storage_path text NOT NULL,
  business_type varchar(64) NOT NULL,
  related_object_type varchar(64),
  related_object_id uuid,
  upload_status varchar(64) NOT NULL DEFAULT 'uploaded',
  uploaded_by uuid REFERENCES users(user_id),
  uploaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS peer_report_files (
  peer_report_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  peer_company_id uuid NOT NULL REFERENCES peer_company_profiles(peer_company_id),
  file_id uuid NOT NULL REFERENCES file_objects(file_id),
  report_year integer NOT NULL,
  report_name varchar(512),
  report_language varchar(32) DEFAULT 'zh',
  page_count integer,
  is_text_pdf boolean,
  parse_status parse_status NOT NULL DEFAULT 'uploaded',
  ai_review_status varchar(64),
  approved_by uuid REFERENCES users(user_id),
  approved_at timestamptz,
  stored_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS async_jobs (
  job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  job_type varchar(128) NOT NULL,
  job_status job_status NOT NULL DEFAULT 'pending',
  progress integer NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  current_step varchar(255),
  target_object_type varchar(64),
  target_object_id uuid,
  request_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by uuid REFERENCES users(user_id),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 10. 同行报告解析结构化结果
-- =========================================================

CREATE TABLE IF NOT EXISTS report_extracted_standards (
  extracted_standard_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  peer_report_id uuid NOT NULL REFERENCES peer_report_files(peer_report_id),
  extracted_standard_name varchar(255) NOT NULL,
  mapped_standard_code varchar(128),
  mapped_standard_name varchar(255),
  standard_version varchar(64),
  adoption_type varchar(64),
  explicit_statement boolean,
  original_action_word varchar(64),
  include_in_adoption_stats boolean NOT NULL DEFAULT false,
  confidence numeric(5,4),
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status NOT NULL DEFAULT 'pending',
  reviewed_by uuid REFERENCES users(user_id),
  reviewed_at timestamptz,
  review_note text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_extracted_topics (
  extracted_topic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  peer_report_id uuid NOT NULL REFERENCES peer_report_files(peer_report_id),
  original_topic_name varchar(255) NOT NULL,
  original_topic_name_en varchar(255),
  mapped_topic_code varchar(128),
  mapped_topic_name varchar(255),
  topic_category esg_category,
  is_material_topic boolean NOT NULL DEFAULT true,
  topic_source_type varchar(64),
  financial_materiality materiality_level DEFAULT 'unknown',
  impact_materiality materiality_level DEFAULT 'unknown',
  double_materiality_result materiality_level DEFAULT 'unknown',
  materiality_basis text,
  mapping_type varchar(64),
  mapping_confidence numeric(5,4),
  confidence numeric(5,4),
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  include_in_topic_stats boolean NOT NULL DEFAULT false,
  review_status review_status NOT NULL DEFAULT 'pending',
  reviewed_by uuid REFERENCES users(user_id),
  reviewed_at timestamptz,
  review_note text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_extracted_metrics (
  extracted_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  peer_report_id uuid NOT NULL REFERENCES peer_report_files(peer_report_id),
  original_metric_name varchar(255) NOT NULL,
  mapped_metric_code varchar(128),
  mapped_metric_name varchar(255),
  related_topic_code varchar(128),
  metric_type metric_type,
  data_type data_type,
  numeric_value numeric,
  text_value text,
  unit varchar(64),
  reporting_period varchar(64),
  organizational_boundary varchar(255),
  is_table_data boolean,
  table_title varchar(255),
  confidence numeric(5,4),
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS report_extracted_cases (
  extracted_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  peer_report_id uuid NOT NULL REFERENCES peer_report_files(peer_report_id),
  case_title varchar(512) NOT NULL,
  case_type varchar(64),
  related_topic_code varchar(128),
  case_summary text,
  case_result text,
  usable_as_peer_reference boolean NOT NULL DEFAULT true,
  caution text,
  confidence numeric(5,4),
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_review_issues (
  ai_review_issue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid REFERENCES report_projects(project_id),
  object_type varchar(64) NOT NULL,
  object_id uuid,
  issue_type varchar(128) NOT NULL,
  severity severity_level NOT NULL DEFAULT 'medium',
  location jsonb NOT NULL DEFAULT '{}'::jsonb,
  description text NOT NULL,
  suggested_fix text,
  must_fix boolean NOT NULL DEFAULT false,
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 11. 推荐结果
-- =========================================================

CREATE TABLE IF NOT EXISTS project_recommendations (
  recommendation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  recommendation_type varchar(64) NOT NULL, -- standard / topic
  item_code varchar(128) NOT NULL,
  item_name varchar(255) NOT NULL,
  adoption_rate numeric(6,4),
  adopted_company_count integer,
  analyzed_report_count integer,
  recommendation_level varchar(32) NOT NULL DEFAULT 'medium',
  financial_materiality_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
  impact_materiality_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
  reason text,
  limitations jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  selected boolean NOT NULL DEFAULT true,
  review_status review_status NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, recommendation_type, item_code)
);

-- =========================================================
-- 12. 议题分配、采集、审核
-- =========================================================

CREATE TABLE IF NOT EXISTS project_topic_assignments (
  assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  project_topic_id uuid NOT NULL REFERENCES project_topics(project_topic_id),
  owner_org_unit_id uuid REFERENCES project_org_units(project_org_unit_id),
  collaborator_org_unit_ids uuid[] NOT NULL DEFAULT '{}',
  collector_user_id uuid REFERENCES users(user_id),
  reviewer_user_id uuid REFERENCES users(user_id),
  due_date date,
  priority varchar(32) DEFAULT 'medium',
  assignment_reason text,
  status status_active NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_topic_id)
);

CREATE TABLE IF NOT EXISTS collection_tasks (
  task_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  project_topic_id uuid NOT NULL REFERENCES project_topics(project_topic_id),
  assignment_id uuid REFERENCES project_topic_assignments(assignment_id),
  task_name varchar(255) NOT NULL,
  owner_org_unit_id uuid REFERENCES project_org_units(project_org_unit_id),
  collector_user_id uuid REFERENCES users(user_id),
  reviewer_user_id uuid REFERENCES users(user_id),
  due_date date,
  task_status task_status NOT NULL DEFAULT 'pending',
  submitted_at timestamptz,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_submissions (
  submission_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  task_id uuid NOT NULL REFERENCES collection_tasks(task_id),
  submitter_user_id uuid REFERENCES users(user_id),
  submission_note text,
  warning_confirmation_note text,
  task_status task_status NOT NULL DEFAULT 'draft',
  submitted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_submission_items (
  submission_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  submission_id uuid NOT NULL REFERENCES task_submissions(submission_id),
  project_topic_metric_id uuid NOT NULL REFERENCES project_topic_metrics(project_topic_metric_id),
  value numeric,
  text_value text,
  unit varchar(64),
  period varchar(64),
  org_unit_id uuid,
  description text,
  attachment_file_ids uuid[] NOT NULL DEFAULT '{}',
  validation_issues jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_reviews (
  task_review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  task_id uuid NOT NULL REFERENCES collection_tasks(task_id),
  submission_id uuid NOT NULL REFERENCES task_submissions(submission_id),
  reviewer_user_id uuid REFERENCES users(user_id),
  review_action varchar(64) NOT NULL,
  review_note text,
  return_items jsonb NOT NULL DEFAULT '[]'::jsonb,
  confirmed_validation_issue_ids uuid[] NOT NULL DEFAULT '{}',
  reviewed_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 13. ESG数据表与知识库
-- =========================================================

CREATE TABLE IF NOT EXISTS esg_data_records (
  data_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  project_topic_id uuid REFERENCES project_topics(project_topic_id),
  project_topic_metric_id uuid REFERENCES project_topic_metrics(project_topic_metric_id),
  topic_code varchar(128),
  topic_name varchar(255),
  metric_code varchar(128),
  metric_name varchar(255),
  data_type data_type,
  value numeric,
  text_value text,
  unit varchar(64),
  period varchar(64),
  org_unit_id uuid,
  org_unit_name varchar(255),
  source_task_id uuid REFERENCES collection_tasks(task_id),
  source_submission_id uuid REFERENCES task_submissions(submission_id),
  source_submission_item_id uuid REFERENCES task_submission_items(submission_item_id),
  source_file_ids uuid[] NOT NULL DEFAULT '{}',
  review_status review_status NOT NULL DEFAULT 'approved',
  report_reference_status varchar(64) NOT NULL DEFAULT 'not_referenced',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
  knowledge_document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  file_id uuid REFERENCES file_objects(file_id),
  document_name varchar(512) NOT NULL,
  document_type varchar(64),
  department_org_unit_id uuid,
  related_topic_codes text[] NOT NULL DEFAULT '{}',
  related_metric_codes text[] NOT NULL DEFAULT '{}',
  year integer,
  review_status review_status NOT NULL DEFAULT 'approved',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  chunk_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  knowledge_document_id uuid NOT NULL REFERENCES knowledge_documents(knowledge_document_id),
  chunk_index integer NOT NULL,
  page_no integer,
  section_title varchar(512),
  table_name varchar(255),
  chunk_text text NOT NULL,
  token_count integer,
  embedding jsonb, -- PoC阶段用jsonb保存向量；生产可改为 pgvector: vector(1536)
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (knowledge_document_id, chunk_index)
);

-- 如果未安装pgvector，上方 embedding vector(1536) 会失败。
-- 生产建议：CREATE EXTENSION IF NOT EXISTS vector; 并根据模型维度调整。
-- 若暂不启用向量检索，可先注释 embedding 字段。

-- =========================================================
-- 14. AI模型、调用日志、输出记录
-- =========================================================

CREATE TABLE IF NOT EXISTS ai_models (
  model_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid REFERENCES tenants(tenant_id),
  provider varchar(128) NOT NULL,
  model_name varchar(255) NOT NULL,
  enabled boolean NOT NULL DEFAULT true,
  capabilities text[] NOT NULL DEFAULT '{}',
  input_price_per_1k_tokens numeric(18,8),
  output_price_per_1k_tokens numeric(18,8),
  is_default boolean NOT NULL DEFAULT false,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_call_logs (
  ai_call_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  user_id uuid REFERENCES users(user_id),
  agent_type varchar(128) NOT NULL,
  prompt_version varchar(128) NOT NULL,
  model_id uuid REFERENCES ai_models(model_id),
  model_provider varchar(128),
  model_name varchar(255),
  input_object_type varchar(64),
  input_object_id uuid,
  input_tokens integer DEFAULT 0,
  output_tokens integer DEFAULT 0,
  total_tokens integer DEFAULT 0,
  input_cost numeric(18,8) DEFAULT 0,
  output_cost numeric(18,8) DEFAULT 0,
  total_cost numeric(18,8) DEFAULT 0,
  call_status ai_call_status NOT NULL,
  error_code varchar(128),
  error_message text,
  retry_count integer NOT NULL DEFAULT 0,
  input_summary text,
  output_summary text,
  started_at timestamptz,
  finished_at timestamptz,
  duration_seconds integer,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_output_records (
  ai_output_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ai_call_id uuid REFERENCES ai_call_logs(ai_call_id),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  agent_type varchar(128) NOT NULL,
  output_object_type varchar(64) NOT NULL,
  output_object_id uuid,
  raw_output jsonb NOT NULL DEFAULT '{}'::jsonb,
  parsed_output jsonb NOT NULL DEFAULT '{}'::jsonb,
  schema_version varchar(32) NOT NULL DEFAULT '1.0',
  parse_status varchar(64) NOT NULL DEFAULT 'parsed',
  validation_errors jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status NOT NULL DEFAULT 'pending',
  adoption_status varchar(64) NOT NULL DEFAULT 'not_adopted',
  adopted_by uuid REFERENCES users(user_id),
  adopted_at timestamptz,
  rejected_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 15. 报告章节、材料包、写作、来源、校对
-- =========================================================

CREATE TABLE IF NOT EXISTS report_chapters (
  chapter_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  chapter_title varchar(255) NOT NULL,
  chapter_order integer NOT NULL DEFAULT 0,
  chapter_level smallint NOT NULL DEFAULT 1,
  parent_chapter_id uuid REFERENCES report_chapters(chapter_id),
  chapter_status varchar(64) NOT NULL DEFAULT 'material_pending',
  related_topic_codes text[] NOT NULL DEFAULT '{}',
  writing_requirements text,
  latest_version_id uuid,
  confirmed_version_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chapter_material_packages (
  material_package_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  chapter_id uuid NOT NULL REFERENCES report_chapters(chapter_id),
  package_version integer NOT NULL DEFAULT 1,
  materials jsonb NOT NULL DEFAULT '{}'::jsonb,
  excluded_materials jsonb NOT NULL DEFAULT '[]'::jsonb,
  missing_information jsonb NOT NULL DEFAULT '[]'::jsonb,
  can_generate_chapter boolean NOT NULL DEFAULT false,
  confirmed_by uuid REFERENCES users(user_id),
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (chapter_id, package_version)
);

CREATE TABLE IF NOT EXISTS chapter_versions (
  chapter_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  chapter_id uuid NOT NULL REFERENCES report_chapters(chapter_id),
  version_no integer NOT NULL,
  version_type varchar(64) NOT NULL, -- ai_generated / manual_edit / imported
  base_version_id uuid REFERENCES chapter_versions(chapter_version_id),
  material_package_id uuid REFERENCES chapter_material_packages(material_package_id),
  content_markdown text NOT NULL,
  language varchar(32) NOT NULL DEFAULT 'zh',
  word_count integer,
  source_claim_count integer NOT NULL DEFAULT 0,
  missing_source_count integer NOT NULL DEFAULT 0,
  created_by uuid REFERENCES users(user_id),
  created_by_type varchar(64) NOT NULL DEFAULT 'user',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (chapter_id, version_no)
);

CREATE TABLE IF NOT EXISTS chapter_claims (
  claim_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  chapter_id uuid NOT NULL REFERENCES report_chapters(chapter_id),
  chapter_version_id uuid NOT NULL REFERENCES chapter_versions(chapter_version_id),
  claim_text text NOT NULL,
  claim_type varchar(64),
  citation_required boolean NOT NULL DEFAULT true,
  suggested_source_ids text[] NOT NULL DEFAULT '{}',
  citation_placeholder varchar(128),
  confidence numeric(5,4),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_references (
  source_reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  target_object_type varchar(64) NOT NULL, -- claim / extracted_topic / data_record / recommendation
  target_object_id uuid NOT NULL,
  source_type source_type NOT NULL,
  source_object_id uuid,
  document_name varchar(512),
  page_no integer,
  section_title varchar(512),
  paragraph_no varchar(64),
  table_name varchar(255),
  row_or_cell varchar(128),
  start_time_sec numeric,
  end_time_sec numeric,
  quoted_text text,
  support_status support_status,
  confidence numeric(5,4),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS citation_results (
  citation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  chapter_id uuid NOT NULL REFERENCES report_chapters(chapter_id),
  chapter_version_id uuid NOT NULL REFERENCES chapter_versions(chapter_version_id),
  claim_id uuid REFERENCES chapter_claims(claim_id),
  claim_text text NOT NULL,
  support_status support_status NOT NULL,
  citation_label varchar(64),
  source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  issue text,
  suggested_fix text,
  requires_fix boolean NOT NULL DEFAULT false,
  confidence numeric(5,4),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chapter_review_issues (
  chapter_review_issue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  chapter_id uuid NOT NULL REFERENCES report_chapters(chapter_id),
  chapter_version_id uuid NOT NULL REFERENCES chapter_versions(chapter_version_id),
  issue_type varchar(128) NOT NULL,
  severity severity_level NOT NULL DEFAULT 'medium',
  location jsonb NOT NULL DEFAULT '{}'::jsonb,
  description text NOT NULL,
  suggested_fix text,
  must_fix boolean NOT NULL DEFAULT false,
  related_source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  review_status review_status NOT NULL DEFAULT 'pending',
  handled_by uuid REFERENCES users(user_id),
  handled_at timestamptz,
  handle_action varchar(64),
  handle_note text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS full_report_reviews (
  full_review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  report_version varchar(64),
  overall_result varchar(64) NOT NULL DEFAULT 'issues_found',
  coverage jsonb NOT NULL DEFAULT '{}'::jsonb,
  issues jsonb NOT NULL DEFAULT '[]'::jsonb,
  can_export boolean NOT NULL DEFAULT false,
  confirmed_by uuid REFERENCES users(user_id),
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 16. 导出与审计
-- =========================================================

CREATE TABLE IF NOT EXISTS report_exports (
  export_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid NOT NULL REFERENCES enterprises(enterprise_id),
  project_id uuid NOT NULL REFERENCES report_projects(project_id),
  export_formats text[] NOT NULL DEFAULT '{}',
  export_options jsonb NOT NULL DEFAULT '{}'::jsonb,
  template_id uuid,
  export_status job_status NOT NULL DEFAULT 'pending',
  file_ids uuid[] NOT NULL DEFAULT '{}',
  created_by uuid REFERENCES users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id),
  enterprise_id uuid REFERENCES enterprises(enterprise_id),
  project_id uuid REFERENCES report_projects(project_id),
  user_id uuid REFERENCES users(user_id),
  user_name varchar(128),
  action_type varchar(128) NOT NULL,
  object_type varchar(64),
  object_id uuid,
  description text,
  before_payload jsonb,
  after_payload jsonb,
  ip_address varchar(128),
  user_agent text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- =========================================================
-- 17. 触发器：updated_at
-- =========================================================

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tenants','enterprises','users','roles','report_projects','org_units',
    'esg_standards','standard_versions','standard_clauses','esg_topics','esg_metrics',
    'peer_company_profiles','peer_report_files','project_topics','collection_tasks',
    'task_submissions','task_submission_items','esg_data_records','ai_models',
    'report_chapters'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_set_updated_at ON esg.%I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%I_set_updated_at BEFORE UPDATE ON esg.%I FOR EACH ROW EXECUTE FUNCTION esg.set_updated_at()', t, t);
  END LOOP;
END $$;

-- =========================================================
-- 18. 索引
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_enterprises_tenant ON enterprises(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_tenant_email ON users(tenant_id, email);
CREATE INDEX IF NOT EXISTS idx_projects_tenant_enterprise ON report_projects(tenant_id, enterprise_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON report_projects(project_status);
CREATE INDEX IF NOT EXISTS idx_org_units_enterprise_parent ON org_units(enterprise_id, parent_org_unit_id);
CREATE INDEX IF NOT EXISTS idx_project_topics_project ON project_topics(project_id);
CREATE INDEX IF NOT EXISTS idx_project_topic_metrics_project_topic ON project_topic_metrics(project_id, project_topic_id);
CREATE INDEX IF NOT EXISTS idx_peer_reports_project_status ON peer_report_files(project_id, parse_status);
CREATE INDEX IF NOT EXISTS idx_jobs_project_status ON async_jobs(project_id, job_status);
CREATE INDEX IF NOT EXISTS idx_extracted_standards_report ON report_extracted_standards(peer_report_id);
CREATE INDEX IF NOT EXISTS idx_extracted_topics_report ON report_extracted_topics(peer_report_id);
CREATE INDEX IF NOT EXISTS idx_extracted_topics_project_topic ON report_extracted_topics(project_id, mapped_topic_code);
CREATE INDEX IF NOT EXISTS idx_recommendations_project_type ON project_recommendations(project_id, recommendation_type);
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON collection_tasks(project_id, task_status);
CREATE INDEX IF NOT EXISTS idx_tasks_collector ON collection_tasks(collector_user_id, task_status);
CREATE INDEX IF NOT EXISTS idx_tasks_reviewer ON collection_tasks(reviewer_user_id, task_status);
CREATE INDEX IF NOT EXISTS idx_esg_data_project_metric ON esg_data_records(project_id, metric_code);
CREATE INDEX IF NOT EXISTS idx_esg_data_project_topic ON esg_data_records(project_id, topic_code);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_project ON knowledge_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_doc ON knowledge_chunks(knowledge_document_id);
CREATE INDEX IF NOT EXISTS idx_ai_call_logs_project_agent ON ai_call_logs(project_id, agent_type);
CREATE INDEX IF NOT EXISTS idx_chapter_versions_chapter ON chapter_versions(chapter_id, version_no);
CREATE INDEX IF NOT EXISTS idx_source_refs_target ON source_references(target_object_type, target_object_id);
CREATE INDEX IF NOT EXISTS idx_chapter_review_issues_version ON chapter_review_issues(chapter_version_id, review_status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_project_created ON audit_logs(project_id, created_at);

-- JSONB GIN索引：用于来源、材料包、覆盖结果等检索
CREATE INDEX IF NOT EXISTS idx_ai_output_records_parsed_gin ON ai_output_records USING gin(parsed_output);
CREATE INDEX IF NOT EXISTS idx_material_packages_materials_gin ON chapter_material_packages USING gin(materials);
CREATE INDEX IF NOT EXISTS idx_full_reviews_issues_gin ON full_report_reviews USING gin(issues);

-- =========================================================
-- 19. 初始系统角色示例
-- =========================================================

-- 注意：以下仅为示例种子数据。正式环境建议使用单独seed脚本。
-- INSERT INTO tenants (tenant_code, tenant_name) VALUES ('DEFAULT', '默认租户') ON CONFLICT DO NOTHING;

-- =========================================================
-- 20. 实施注意事项
-- =========================================================

-- 1. 多租户隔离：所有业务表必须带 tenant_id，应用层查询必须强制按 tenant_id 过滤。
-- 2. 项目快照：project_topics、project_topic_metrics、project_standards 应保存项目当时确认状态。
-- 3. AI结果：ai_output_records 必须保存 raw_output 与 parsed_output，方便审计和复盘。
-- 4. 来源引用：source_references 与 citation_results 是报告可信度核心，不建议简化。
-- 5. 知识库向量：如果暂不启用pgvector，可删除 knowledge_chunks.embedding 字段。
-- 6. 生产权限：建议结合 PostgreSQL RLS 或应用层租户过滤实现强隔离。
-- 7. 外键策略：此DDL默认保守，不做级联删除。历史数据建议停用而非物理删除。
