-- ESG报告软件 数据库种子数据 SQL v0.1
-- 依赖：请先执行 ESG_PostgreSQL_DDL_v0.1.sql
-- 目标：初始化开发/PoC/MVP演示环境的基础数据。
-- 覆盖：默认租户、系统角色、示例用户、示例企业、GICS、标准、标准版本、条款、
--      议题、指标、映射、校验规则、证据要求、别名、部门推荐规则、AI模型。

BEGIN;

SET search_path TO esg, public;

-- =========================================================
-- 1. 默认租户
-- =========================================================

INSERT INTO tenants (tenant_code, tenant_name, status, settings)
VALUES
  ('DEFAULT', '默认演示租户', 'active', '{"purpose":"demo_seed"}'::jsonb)
ON CONFLICT (tenant_code) DO UPDATE
SET tenant_name = EXCLUDED.tenant_name,
    status = EXCLUDED.status,
    updated_at = now();

-- =========================================================
-- 2. 系统角色
-- =========================================================

INSERT INTO roles (tenant_id, role_code, role_name, role_description, permissions, is_system_role, status)
SELECT t.tenant_id, v.role_code, v.role_name, v.role_description, v.permissions::jsonb, true, 'active'
FROM tenants t
CROSS JOIN (
  VALUES
  ('platform_admin', '平台管理员', '管理平台级租户、系统配置和全局数据', '["*"]'),
  ('tenant_admin', '租户管理员', '管理当前租户下企业、用户、权限和配置', '["tenant:*","enterprise:*","user:*","project:*","ai_cost:read"]'),
  ('enterprise_admin', '企业管理员', '管理单企业配置、用户和项目', '["enterprise:read","enterprise:update","project:*","user:read"]'),
  ('project_owner', '项目负责人', '管理ESG报告项目全流程', '["project:*","topic:*","task:*","chapter:*","export:*","ai:*","file:upload"]'),
  ('esg_expert', 'ESG专家', '审核标准库、同行解析结果和AI输出质量', '["standard:read","topic:read","metric:read","peer_report:review","ai_review:*"]'),
  ('standard_admin', '标准库管理员', '维护标准、议题、指标、映射和校验规则', '["standard:*","topic:*","metric:*"]'),
  ('department_collector', '部门采集员', '填报部门采集任务', '["collection_task:read_assigned","collection_task:write_assigned","file:upload"]'),
  ('department_reviewer', '部门审核员', '审核部门填报任务', '["review_task:read_assigned","review_task:review_assigned"]'),
  ('report_writer', '报告编写人员', '使用知识库和AI进行章节写作', '["chapter:read","chapter:write","chapter:generate","citation:*"]'),
  ('final_approver', '最终确认人', '确认章节、全文和导出报告', '["chapter:confirm","full_review:confirm","export:*"]')
) AS v(role_code, role_name, role_description, permissions)
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (tenant_id, role_code) DO UPDATE
SET role_name = EXCLUDED.role_name,
    role_description = EXCLUDED.role_description,
    permissions = EXCLUDED.permissions,
    is_system_role = true,
    status = 'active',
    updated_at = now();

-- =========================================================
-- 3. 示例用户
-- =========================================================

INSERT INTO users (tenant_id, name, email, phone, password_hash, status)
SELECT t.tenant_id, v.name, v.email, v.phone, 'pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$TYS3ovZYqJ2bTLGKaJj2isqd+keujkLbW75Xrp0lJf8=', 'active'
FROM tenants t
CROSS JOIN (
  VALUES
  ('系统管理员', 'admin@example.com', '13800000001'),
  ('项目负责人', 'project.owner@example.com', '13800000002'),
  ('ESG专家', 'esg.expert@example.com', '13800000003'),
  ('EHS采集员', 'ehs.collector@example.com', '13800000004'),
  ('EHS审核员', 'ehs.reviewer@example.com', '13800000005'),
  ('HR采集员', 'hr.collector@example.com', '13800000006'),
  ('HR审核员', 'hr.reviewer@example.com', '13800000007')
) AS v(name, email, phone)
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (tenant_id, email) DO UPDATE
SET name = EXCLUDED.name,
    phone = EXCLUDED.phone,
    password_hash = CASE
      WHEN users.password_hash IS NULL
        OR users.password_hash = ''
        OR users.password_hash IN (
          'pbkdf2_sha256$120000$SMMW4Xbdu34FhUkKPIq5Mw==$Y+tg83U5LG8+OiidKae8grhDMIM+C98K3GtnQMvJ1dY='
        )
        THEN EXCLUDED.password_hash
      ELSE users.password_hash
    END,
    status = 'active',
    updated_at = now();

-- 角色分配
INSERT INTO user_roles (tenant_id, user_id, role_id)
SELECT t.tenant_id, u.user_id, r.role_id
FROM tenants t
JOIN users u ON u.tenant_id = t.tenant_id
JOIN roles r ON r.tenant_id = t.tenant_id
JOIN (
  VALUES
  ('admin@example.com', 'tenant_admin'),
  ('project.owner@example.com', 'project_owner'),
  ('esg.expert@example.com', 'esg_expert'),
  ('ehs.collector@example.com', 'department_collector'),
  ('ehs.reviewer@example.com', 'department_reviewer'),
  ('hr.collector@example.com', 'department_collector'),
  ('hr.reviewer@example.com', 'department_reviewer')
) AS m(email, role_code)
ON u.email = m.email AND r.role_code = m.role_code
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (user_id, role_id, enterprise_id, project_id, org_unit_id) DO NOTHING;

-- =========================================================
-- 4. 示例企业
-- =========================================================

INSERT INTO enterprises (
  tenant_id, enterprise_code, enterprise_name, enterprise_short_name, stock_code, exchange,
  country_or_region, industry_description, main_business, status
)
SELECT t.tenant_id, 'ENT_DEMO', '示例股份有限公司', '示例股份', '600001', 'SSE',
       'CN', '工业机械设备制造', '工业设备研发、制造、销售和服务', 'active'
FROM tenants t
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (tenant_id, enterprise_code) DO UPDATE
SET enterprise_name = EXCLUDED.enterprise_name,
    enterprise_short_name = EXCLUDED.enterprise_short_name,
    stock_code = EXCLUDED.stock_code,
    exchange = EXCLUDED.exchange,
    industry_description = EXCLUDED.industry_description,
    main_business = EXCLUDED.main_business,
    updated_at = now();

-- =========================================================
-- 5. GICS示例数据
-- =========================================================

INSERT INTO gics_industries (gics_code, gics_name_en, gics_name_cn, gics_level, parent_gics_code, status)
VALUES
  ('20', 'Industrials', '工业', 1, NULL, 'active'),
  ('2010', 'Capital Goods', '资本货物', 2, '20', 'active'),
  ('201060', 'Machinery', '机械', 3, '2010', 'active'),
  ('20106010', 'Industrial Machinery', '工业机械', 4, '201060', 'active'),
  ('20106020', 'Construction Machinery & Heavy Transportation Equipment', '工程机械与重型运输设备', 4, '201060', 'active'),
  ('15', 'Materials', '材料', 1, NULL, 'active'),
  ('1510', 'Materials', '材料', 2, '15', 'active'),
  ('151010', 'Chemicals', '化工', 3, '1510', 'active'),
  ('15101050', 'Specialty Chemicals', '特种化学品', 4, '151010', 'active'),
  ('45', 'Information Technology', '信息技术', 1, NULL, 'active'),
  ('4520', 'Technology Hardware & Equipment', '技术硬件与设备', 2, '45', 'active'),
  ('452030', 'Electronic Equipment, Instruments & Components', '电子设备、仪器和元件', 3, '4520', 'active'),
  ('45203010', 'Electronic Equipment & Instruments', '电子设备与仪器', 4, '452030', 'active')
ON CONFLICT (gics_code) DO UPDATE
SET gics_name_en = EXCLUDED.gics_name_en,
    gics_name_cn = EXCLUDED.gics_name_cn,
    gics_level = EXCLUDED.gics_level,
    parent_gics_code = EXCLUDED.parent_gics_code,
    status = 'active';

INSERT INTO enterprise_gics_history (
  tenant_id, enterprise_id, gics_level, gics_code, confidence, source, reason, is_current, confirmed_by, confirmed_at
)
SELECT t.tenant_id, e.enterprise_id, 4, '20106010', 0.8600, 'seed',
       '示例企业主营业务为工业机械设备制造，匹配工业机械GICS四级行业。',
       true, u.user_id, now()
FROM tenants t
JOIN enterprises e ON e.tenant_id = t.tenant_id AND e.enterprise_code = 'ENT_DEMO'
LEFT JOIN users u ON u.tenant_id = t.tenant_id AND u.email = 'project.owner@example.com'
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT DO NOTHING;

-- 同行公司示例池
INSERT INTO peer_company_profiles (company_name, company_short_name, stock_code, exchange, gics_level_4_code, gics_level_4_name, main_business, metadata)
VALUES
  ('工业机械同行A股份有限公司', '同行A', '600101', 'SSE', '20106010', '工业机械', '工业自动化设备和通用机械制造', '{"seed":true}'::jsonb),
  ('智能装备同行B股份有限公司', '同行B', '000202', 'SZSE', '20106010', '工业机械', '智能装备、工业机器人和成套设备制造', '{"seed":true}'::jsonb),
  ('重型装备同行C股份有限公司', '同行C', '601303', 'SSE', '20106020', '工程机械与重型运输设备', '工程机械和重型运输设备制造', '{"seed":true}'::jsonb),
  ('特种化学同行D股份有限公司', '同行D', '300404', 'SZSE', '15101050', '特种化学品', '精细化工和特种材料研发生产', '{"seed":true}'::jsonb)
ON CONFLICT (stock_code, exchange) DO UPDATE
SET company_name = EXCLUDED.company_name,
    company_short_name = EXCLUDED.company_short_name,
    gics_level_4_code = EXCLUDED.gics_level_4_code,
    gics_level_4_name = EXCLUDED.gics_level_4_name,
    main_business = EXCLUDED.main_business,
    metadata = EXCLUDED.metadata,
    updated_at = now();

-- =========================================================
-- 6. 组织架构示例
-- =========================================================

INSERT INTO org_units (tenant_id, enterprise_id, parent_org_unit_id, org_unit_code, org_unit_name, org_unit_type, sort_order, status)
SELECT t.tenant_id, e.enterprise_id, NULL, 'ORG_ROOT', '示例股份有限公司', 'group', 1, 'active'
FROM tenants t
JOIN enterprises e ON e.tenant_id = t.tenant_id AND e.enterprise_code = 'ENT_DEMO'
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (enterprise_id, org_unit_code) DO UPDATE
SET org_unit_name = EXCLUDED.org_unit_name,
    org_unit_type = EXCLUDED.org_unit_type,
    updated_at = now();

INSERT INTO org_units (tenant_id, enterprise_id, parent_org_unit_id, org_unit_code, org_unit_name, org_unit_type, sort_order, status)
SELECT t.tenant_id, e.enterprise_id, root.org_unit_id, v.org_unit_code, v.org_unit_name, 'department', v.sort_order, 'active'
FROM tenants t
JOIN enterprises e ON e.tenant_id = t.tenant_id AND e.enterprise_code = 'ENT_DEMO'
JOIN org_units root ON root.enterprise_id = e.enterprise_id AND root.org_unit_code = 'ORG_ROOT'
CROSS JOIN (
  VALUES
  ('ORG_EHS', 'EHS部门', 10),
  ('ORG_HR', '人力资源部', 20),
  ('ORG_PROCUREMENT', '采购部', 30),
  ('ORG_FINANCE', '财务部', 40),
  ('ORG_LEGAL', '法务合规部', 50),
  ('ORG_BOARD_OFFICE', '董秘办', 60),
  ('ORG_PRODUCTION', '生产部', 70)
) AS v(org_unit_code, org_unit_name, sort_order)
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (enterprise_id, org_unit_code) DO UPDATE
SET org_unit_name = EXCLUDED.org_unit_name,
    parent_org_unit_id = EXCLUDED.parent_org_unit_id,
    sort_order = EXCLUDED.sort_order,
    updated_at = now();

-- 组织成员示例
INSERT INTO org_unit_users (tenant_id, org_unit_id, user_id, assignment_role, status)
SELECT t.tenant_id, ou.org_unit_id, u.user_id, v.assignment_role, 'active'
FROM tenants t
JOIN enterprises e ON e.tenant_id = t.tenant_id AND e.enterprise_code = 'ENT_DEMO'
JOIN (
  VALUES
  ('ORG_EHS', 'ehs.collector@example.com', 'collector'),
  ('ORG_EHS', 'ehs.reviewer@example.com', 'reviewer'),
  ('ORG_HR', 'hr.collector@example.com', 'collector'),
  ('ORG_HR', 'hr.reviewer@example.com', 'reviewer')
) AS v(org_unit_code, email, assignment_role)
  ON true
JOIN org_units ou ON ou.enterprise_id = e.enterprise_id AND ou.org_unit_code = v.org_unit_code
JOIN users u ON u.tenant_id = t.tenant_id AND u.email = v.email
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (org_unit_id, user_id, assignment_role) DO UPDATE
SET status = 'active';

-- =========================================================
-- 7. ESG标准
-- =========================================================

INSERT INTO esg_standards (
  standard_code, standard_name, standard_short_name, standard_type,
  applicable_market, issuing_body, description, scope_type, status
)
VALUES
  ('STD_GRI', 'GRI Standards', 'GRI', 'voluntary', 'global', 'Global Reporting Initiative', '通用可持续发展报告标准。', 'platform_public', 'active'),
  ('STD_IFRS_S1', 'IFRS S1', 'IFRS S1', 'voluntary', 'global', 'ISSB', '可持续相关财务信息披露通用要求。', 'platform_public', 'active'),
  ('STD_IFRS_S2', 'IFRS S2', 'IFRS S2', 'voluntary', 'global', 'ISSB', '气候相关披露要求。', 'platform_public', 'active'),
  ('STD_SSE_SUSTAINABILITY', '上海证券交易所可持续发展报告指引', '上交所指引', 'mandatory_or_guidance', 'A_share', '上海证券交易所', 'A股可持续发展报告披露相关指引。', 'platform_public', 'active'),
  ('STD_SZSE_SUSTAINABILITY', '深圳证券交易所可持续发展报告指引', '深交所指引', 'mandatory_or_guidance', 'A_share', '深圳证券交易所', 'A股可持续发展报告披露相关指引。', 'platform_public', 'active'),
  ('STD_BSE_SUSTAINABILITY', '北京证券交易所可持续发展报告指引', '北交所指引', 'mandatory_or_guidance', 'A_share', '北京证券交易所', 'A股可持续发展报告披露相关指引。', 'platform_public', 'active'),
  ('STD_HKEX_ESG', '港交所ESG报告指引', '港交所ESG', 'mandatory_or_guidance', 'HKEX', '香港交易所', '香港上市公司ESG披露相关指引。', 'platform_public', 'active')
ON CONFLICT (standard_code) DO UPDATE
SET standard_name = EXCLUDED.standard_name,
    standard_short_name = EXCLUDED.standard_short_name,
    standard_type = EXCLUDED.standard_type,
    applicable_market = EXCLUDED.applicable_market,
    issuing_body = EXCLUDED.issuing_body,
    description = EXCLUDED.description,
    status = 'active',
    updated_at = now();

-- 标准版本
INSERT INTO standard_versions (standard_id, standard_version_code, version_name, version_no, effective_date, is_current, status)
SELECT s.standard_id, v.standard_version_code, v.version_name, v.version_no, v.effective_date::date, true, 'active'
FROM esg_standards s
JOIN (
  VALUES
  ('STD_GRI', 'STD_GRI_2021', '2021版', '2021', '2021-01-01'),
  ('STD_IFRS_S1', 'STD_IFRS_S1_2023', '2023版', '2023', '2023-01-01'),
  ('STD_IFRS_S2', 'STD_IFRS_S2_2023', '2023版', '2023', '2023-01-01'),
  ('STD_SSE_SUSTAINABILITY', 'STD_SSE_SUSTAINABILITY_V1', '示例版本', 'v1', '2024-01-01'),
  ('STD_SZSE_SUSTAINABILITY', 'STD_SZSE_SUSTAINABILITY_V1', '示例版本', 'v1', '2024-01-01'),
  ('STD_BSE_SUSTAINABILITY', 'STD_BSE_SUSTAINABILITY_V1', '示例版本', 'v1', '2024-01-01'),
  ('STD_HKEX_ESG', 'STD_HKEX_ESG_V1', '示例版本', 'v1', '2024-01-01')
) AS v(standard_code, standard_version_code, version_name, version_no, effective_date)
ON s.standard_code = v.standard_code
ON CONFLICT (standard_version_code) DO UPDATE
SET version_name = EXCLUDED.version_name,
    version_no = EXCLUDED.version_no,
    effective_date = EXCLUDED.effective_date,
    is_current = true,
    status = 'active',
    updated_at = now();

-- 标准条款示例
INSERT INTO standard_clauses (
  standard_version_id, clause_code, clause_no, clause_title, parent_clause_code,
  clause_level, clause_text, clause_summary, disclosure_type, is_required, applicable_condition, status
)
SELECT sv.standard_version_id, v.clause_code, v.clause_no, v.clause_title, v.parent_clause_code,
       v.clause_level, v.clause_text, v.clause_summary, v.disclosure_type, v.is_required, v.applicable_condition, 'active'
FROM standard_versions sv
JOIN (
  VALUES
  ('STD_GRI_2021', 'GRI_305_1', 'GRI 305-1', '直接温室气体排放', 'GRI_305', 2, '披露组织的直接温室气体排放量。', '披露范围一排放量。', 'quantitative', 'yes', '存在直接排放时适用'),
  ('STD_GRI_2021', 'GRI_305_2', 'GRI 305-2', '能源间接温室气体排放', 'GRI_305', 2, '披露组织的能源间接温室气体排放量。', '披露范围二排放量。', 'quantitative', 'yes', '存在购入能源时适用'),
  ('STD_GRI_2021', 'GRI_302_1', 'GRI 302-1', '组织内部能源消耗', 'GRI_302', 2, '披露组织内部能源消耗。', '披露能源消耗数据。', 'quantitative', 'yes', '存在能源消耗时适用'),
  ('STD_GRI_2021', 'GRI_303_3', 'GRI 303-3', '取水量', 'GRI_303', 2, '披露按来源划分的取水量。', '披露取水量。', 'quantitative', 'conditional', '水资源为重要议题时适用'),
  ('STD_GRI_2021', 'GRI_306_3', 'GRI 306-3', '产生的废弃物', 'GRI_306', 2, '披露产生的废弃物总量及构成。', '披露废弃物数据。', 'quantitative', 'conditional', '废弃物为重要议题时适用'),
  ('STD_GRI_2021', 'GRI_403_9', 'GRI 403-9', '工伤', 'GRI_403', 2, '披露工伤相关信息。', '披露职业健康安全指标。', 'quantitative', 'conditional', '职业健康安全为重要议题时适用'),
  ('STD_GRI_2021', 'GRI_404_1', 'GRI 404-1', '每名员工每年接受培训的平均小时数', 'GRI_404', 2, '披露员工培训时长。', '披露培训相关指标。', 'quantitative', 'conditional', '员工培训为重要议题时适用'),
  ('STD_IFRS_S2_2023', 'IFRS_S2_GOV', 'IFRS S2 Governance', '气候相关治理', NULL, 1, '披露用于监测和管理气候相关风险与机遇的治理流程、控制和程序。', '披露气候治理。', 'qualitative', 'conditional', '气候相关议题适用'),
  ('STD_IFRS_S2_2023', 'IFRS_S2_GHG', 'IFRS S2 GHG Emissions', '温室气体排放', NULL, 1, '披露范围一、范围二以及适用情况下的范围三温室气体排放。', '披露温室气体排放。', 'quantitative', 'conditional', '气候相关议题适用'),
  ('STD_SSE_SUSTAINABILITY_V1', 'SSE_ENV_GHG', '环境信息-温室气体', '温室气体排放披露', NULL, 1, '披露温室气体排放相关管理、目标和绩效。', '披露温室气体排放。', 'mixed', 'conditional', '环境议题重要时适用'),
  ('STD_HKEX_ESG_V1', 'HKEX_A1', 'A1 Emissions', '排放物', NULL, 1, '披露排放物及相关管理情况。', '披露排放相关信息。', 'mixed', 'conditional', '存在相关排放时适用')
) AS v(standard_version_code, clause_code, clause_no, clause_title, parent_clause_code, clause_level, clause_text, clause_summary, disclosure_type, is_required, applicable_condition)
ON sv.standard_version_code = v.standard_version_code
ON CONFLICT (clause_code) DO UPDATE
SET clause_title = EXCLUDED.clause_title,
    clause_text = EXCLUDED.clause_text,
    clause_summary = EXCLUDED.clause_summary,
    disclosure_type = EXCLUDED.disclosure_type,
    is_required = EXCLUDED.is_required,
    applicable_condition = EXCLUDED.applicable_condition,
    status = 'active',
    updated_at = now();

-- =========================================================
-- 8. 议题库
-- =========================================================

INSERT INTO esg_topics (
  topic_code, topic_name, topic_category, topic_description,
  default_financial_materiality, default_impact_materiality,
  common_disclosure, default_owner_department, is_common, status
)
VALUES
  ('TOPIC_CLIMATE_CHANGE', '气候变化', 'E', '气候相关治理、战略、风险管理、指标和目标。', 'high', 'high', '气候治理、气候风险、减排目标、温室气体排放。', 'EHS部门', true, 'active'),
  ('TOPIC_GHG_EMISSIONS', '温室气体排放', 'E', '范围一、范围二、范围三温室气体排放及管理。', 'high', 'high', '排放量、核算边界、减排措施。', 'EHS部门', true, 'active'),
  ('TOPIC_ENERGY_MANAGEMENT', '能源管理', 'E', '能源消耗、能源效率和节能管理。', 'medium', 'high', '能源消耗、节能措施、能源结构。', 'EHS部门', true, 'active'),
  ('TOPIC_WATER_MANAGEMENT', '水资源管理', 'E', '取水、用水、排水和水资源效率。', 'medium', 'high', '取水量、用水效率、水风险。', 'EHS部门', true, 'active'),
  ('TOPIC_WASTE_MANAGEMENT', '废弃物管理', 'E', '一般废弃物、危险废弃物、回收利用。', 'medium', 'high', '废弃物产生量、处置方式、回收。', 'EHS部门', true, 'active'),
  ('TOPIC_EMPLOYMENT', '员工雇佣', 'S', '员工结构、薪酬福利、劳动关系。', 'medium', 'medium', '员工人数、员工流失率、雇佣政策。', '人力资源部', true, 'active'),
  ('TOPIC_EMPLOYEE_TRAINING', '员工培训与发展', 'S', '员工培训、职业发展和能力建设。', 'medium', 'medium', '培训小时、培训覆盖率、发展计划。', '人力资源部', true, 'active'),
  ('TOPIC_OCCUPATIONAL_HEALTH_SAFETY', '职业健康与安全', 'S', '职业健康安全管理、工伤、事故和培训。', 'high', 'high', '安全管理体系、工伤率、事故。', 'EHS部门', true, 'active'),
  ('TOPIC_SUPPLY_CHAIN', '供应链管理', 'S', '供应商准入、评估、ESG风险和责任采购。', 'medium', 'high', '供应商数量、评估覆盖率、整改。', '采购部', true, 'active'),
  ('TOPIC_PRODUCT_QUALITY', '产品质量与安全', 'S', '产品质量管理、客户责任和产品安全。', 'high', 'medium', '质量管理、召回、客户投诉。', '质量管理部', true, 'active'),
  ('TOPIC_CORPORATE_GOVERNANCE', '公司治理', 'G', '董事会治理、治理结构和治理机制。', 'high', 'medium', '董事会、治理结构、治理政策。', '董秘办', true, 'active'),
  ('TOPIC_BUSINESS_ETHICS', '商业道德与合规', 'G', '反腐败、商业道德、合规管理。', 'high', 'medium', '合规制度、举报机制、反腐败培训。', '法务合规部', true, 'active'),
  ('TOPIC_RISK_MANAGEMENT', '风险管理', 'G', '风险识别、评估、管理和内控。', 'high', 'medium', '风险管理体系、内控机制。', '法务合规部', true, 'active')
ON CONFLICT (topic_code) DO UPDATE
SET topic_name = EXCLUDED.topic_name,
    topic_category = EXCLUDED.topic_category,
    topic_description = EXCLUDED.topic_description,
    default_financial_materiality = EXCLUDED.default_financial_materiality,
    default_impact_materiality = EXCLUDED.default_impact_materiality,
    common_disclosure = EXCLUDED.common_disclosure,
    default_owner_department = EXCLUDED.default_owner_department,
    is_common = EXCLUDED.is_common,
    status = 'active',
    updated_at = now();

-- =========================================================
-- 9. 指标库
-- =========================================================

INSERT INTO esg_metrics (
  metric_code, metric_name, metric_type, data_type, default_unit,
  reporting_frequency, is_reusable, metric_description, filling_instruction,
  calculation_method, evidence_requirement_text, default_required, status
)
VALUES
  ('METRIC_SCOPE1_GHG', '范围一温室气体排放量', 'quantitative', 'number', 'tCO2e', 'annual', true, '报告期内范围一温室气体排放总量。', '请按报告边界填写范围一温室气体排放总量。', '按企业温室气体核算规则计算。', '上传温室气体排放核算表。', true, 'active'),
  ('METRIC_SCOPE2_GHG', '范围二温室气体排放量', 'quantitative', 'number', 'tCO2e', 'annual', true, '报告期内范围二温室气体排放总量。', '请按报告边界填写范围二温室气体排放总量。', '按企业温室气体核算规则计算。', '上传温室气体排放核算表。', true, 'active'),
  ('METRIC_SCOPE3_GHG', '范围三温室气体排放量', 'quantitative', 'number', 'tCO2e', 'annual', true, '报告期内范围三温室气体排放总量。', '如已统计，请填写范围三温室气体排放总量。', '按适用核算规则计算。', '上传范围三排放核算说明。', false, 'active'),
  ('METRIC_TOTAL_ENERGY', '综合能源消耗量', 'quantitative', 'number', 'tce', 'annual', true, '报告期内综合能源消耗。', '请填写报告期内综合能源消耗。', '按能源折标规则计算。', '上传能源统计表。', false, 'active'),
  ('METRIC_ELECTRICITY_CONSUMPTION', '用电量', 'quantitative', 'number', 'kWh', 'annual', true, '报告期内用电总量。', '请填写报告期内用电量。', '按电费账单或能源系统统计。', '上传电费账单或能源统计表。', false, 'active'),
  ('METRIC_WATER_WITHDRAWAL', '取水量', 'quantitative', 'number', 'm3', 'annual', true, '报告期内取水总量。', '请填写报告期内总取水量。', '按水表或账单统计。', '上传水费账单或取水统计表。', false, 'active'),
  ('METRIC_TOTAL_WASTE', '废弃物产生量', 'quantitative', 'number', 'tonne', 'annual', true, '报告期内废弃物产生总量。', '请填写报告期内废弃物产生总量。', '按废弃物台账统计。', '上传废弃物台账。', false, 'active'),
  ('METRIC_HAZARDOUS_WASTE', '危险废弃物产生量', 'quantitative', 'number', 'tonne', 'annual', true, '报告期内危险废弃物产生总量。', '请填写报告期内危险废弃物产生量。', '按危废台账统计。', '上传危废转移联单或台账。', false, 'active'),
  ('METRIC_TOTAL_EMPLOYEES', '员工总人数', 'quantitative', 'number', 'person', 'annual', true, '报告期末员工总人数。', '请填写报告期末员工总人数。', '按HR系统统计。', '上传员工人数统计表。', true, 'active'),
  ('METRIC_EMPLOYEE_TURNOVER_RATE', '员工流失率', 'quantitative', 'percentage', '%', 'annual', true, '报告期员工流失率。', '请填写报告期员工流失率。', '离职人数/平均员工人数。', '上传员工流失率统计表。', false, 'active'),
  ('METRIC_TRAINING_HOURS', '员工培训总时长', 'quantitative', 'number', 'hour', 'annual', true, '报告期员工培训总小时数。', '请填写报告期内员工培训总时长。', '按培训系统或培训记录统计。', '上传培训记录表。', false, 'active'),
  ('METRIC_TRAINING_COVERAGE', '员工培训覆盖率', 'quantitative', 'percentage', '%', 'annual', true, '报告期员工培训覆盖率。', '请填写培训覆盖率。', '参加培训员工数/员工总数。', '上传培训记录表。', false, 'active'),
  ('METRIC_WORK_INJURY_COUNT', '工伤事故数量', 'quantitative', 'number', 'case', 'annual', true, '报告期工伤事故数量。', '请填写报告期工伤事故数量。', '按安全事故记录统计。', '上传安全事故记录。', false, 'active'),
  ('METRIC_SUPPLIER_COUNT', '供应商总数', 'quantitative', 'number', 'supplier', 'annual', true, '报告期供应商总数。', '请填写报告期供应商总数。', '按采购系统统计。', '上传供应商清单。', false, 'active'),
  ('METRIC_SUPPLIER_ESG_ASSESSMENT_RATE', '供应商ESG评估覆盖率', 'quantitative', 'percentage', '%', 'annual', true, '报告期供应商ESG评估覆盖率。', '请填写接受ESG评估的供应商比例。', '被评估供应商数/供应商总数。', '上传供应商评估记录。', false, 'active'),
  ('METRIC_CLIMATE_GOVERNANCE_DESC', '气候治理机制说明', 'qualitative', 'text', NULL, 'annual', true, '说明公司气候治理架构和职责。', '请说明气候相关治理架构、职责和管理机制。', NULL, '上传相关制度或会议材料。', true, 'active'),
  ('METRIC_ENV_MANAGEMENT_DESC', '环境管理机制说明', 'qualitative', 'text', NULL, 'annual', true, '说明环境管理制度、职责和措施。', '请说明环境管理制度和主要措施。', NULL, '上传环境管理制度。', true, 'active'),
  ('METRIC_BUSINESS_ETHICS_DESC', '商业道德与合规机制说明', 'qualitative', 'text', NULL, 'annual', true, '说明商业道德、反腐败和合规机制。', '请说明商业道德与合规管理机制。', NULL, '上传合规制度或培训记录。', true, 'active')
ON CONFLICT (metric_code) DO UPDATE
SET metric_name = EXCLUDED.metric_name,
    metric_type = EXCLUDED.metric_type,
    data_type = EXCLUDED.data_type,
    default_unit = EXCLUDED.default_unit,
    filling_instruction = EXCLUDED.filling_instruction,
    calculation_method = EXCLUDED.calculation_method,
    evidence_requirement_text = EXCLUDED.evidence_requirement_text,
    default_required = EXCLUDED.default_required,
    status = 'active',
    updated_at = now();

-- =========================================================
-- 10. 标准-议题映射、议题-指标映射、条款-指标映射
-- =========================================================

INSERT INTO standard_topic_maps (standard_version_id, topic_id, related_clause_codes, is_key_topic, applicability_note, status)
SELECT sv.standard_version_id, t.topic_id, v.related_clause_codes, v.is_key_topic, v.applicability_note, 'active'
FROM (
  VALUES
  ('STD_GRI_2021', 'TOPIC_GHG_EMISSIONS', ARRAY['GRI_305_1','GRI_305_2'], true, '适用于披露温室气体排放的企业。'),
  ('STD_GRI_2021', 'TOPIC_ENERGY_MANAGEMENT', ARRAY['GRI_302_1'], true, '适用于披露能源消耗的企业。'),
  ('STD_GRI_2021', 'TOPIC_WATER_MANAGEMENT', ARRAY['GRI_303_3'], false, '水资源为重要议题时适用。'),
  ('STD_GRI_2021', 'TOPIC_WASTE_MANAGEMENT', ARRAY['GRI_306_3'], false, '废弃物为重要议题时适用。'),
  ('STD_GRI_2021', 'TOPIC_EMPLOYEE_TRAINING', ARRAY['GRI_404_1'], false, '员工培训为重要议题时适用。'),
  ('STD_GRI_2021', 'TOPIC_OCCUPATIONAL_HEALTH_SAFETY', ARRAY['GRI_403_9'], true, '职业健康安全为重要议题时适用。'),
  ('STD_IFRS_S2_2023', 'TOPIC_CLIMATE_CHANGE', ARRAY['IFRS_S2_GOV','IFRS_S2_GHG'], true, '气候相关议题适用。'),
  ('STD_IFRS_S2_2023', 'TOPIC_GHG_EMISSIONS', ARRAY['IFRS_S2_GHG'], true, '气候相关排放披露适用。'),
  ('STD_SSE_SUSTAINABILITY_V1', 'TOPIC_GHG_EMISSIONS', ARRAY['SSE_ENV_GHG'], true, '环境议题重要时适用。'),
  ('STD_HKEX_ESG_V1', 'TOPIC_GHG_EMISSIONS', ARRAY['HKEX_A1'], true, '存在相关排放时适用。')
) AS v(standard_version_code, topic_code, related_clause_codes, is_key_topic, applicability_note)
JOIN standard_versions sv ON sv.standard_version_code = v.standard_version_code
JOIN esg_topics t ON t.topic_code = v.topic_code
ON CONFLICT (standard_version_id, topic_id) DO UPDATE
SET related_clause_codes = EXCLUDED.related_clause_codes,
    is_key_topic = EXCLUDED.is_key_topic,
    applicability_note = EXCLUDED.applicability_note,
    status = 'active';

INSERT INTO topic_metric_maps (topic_id, metric_id, default_selected, is_required, sort_order, recommended_collector_role, recommended_reviewer_role, status)
SELECT t.topic_id, m.metric_id, v.default_selected, v.is_required, v.sort_order, v.collector_role, v.reviewer_role, 'active'
FROM (
  VALUES
  ('TOPIC_CLIMATE_CHANGE', 'METRIC_CLIMATE_GOVERNANCE_DESC', true, true, 1, 'EHS专员', 'EHS负责人'),
  ('TOPIC_CLIMATE_CHANGE', 'METRIC_SCOPE1_GHG', true, true, 2, 'EHS专员', 'EHS负责人'),
  ('TOPIC_CLIMATE_CHANGE', 'METRIC_SCOPE2_GHG', true, true, 3, 'EHS专员', 'EHS负责人'),
  ('TOPIC_CLIMATE_CHANGE', 'METRIC_SCOPE3_GHG', true, false, 4, 'EHS专员', 'EHS负责人'),
  ('TOPIC_GHG_EMISSIONS', 'METRIC_SCOPE1_GHG', true, true, 1, 'EHS专员', 'EHS负责人'),
  ('TOPIC_GHG_EMISSIONS', 'METRIC_SCOPE2_GHG', true, true, 2, 'EHS专员', 'EHS负责人'),
  ('TOPIC_GHG_EMISSIONS', 'METRIC_SCOPE3_GHG', true, false, 3, 'EHS专员', 'EHS负责人'),
  ('TOPIC_ENERGY_MANAGEMENT', 'METRIC_TOTAL_ENERGY', true, false, 1, 'EHS专员', 'EHS负责人'),
  ('TOPIC_ENERGY_MANAGEMENT', 'METRIC_ELECTRICITY_CONSUMPTION', true, false, 2, 'EHS专员', 'EHS负责人'),
  ('TOPIC_WATER_MANAGEMENT', 'METRIC_WATER_WITHDRAWAL', true, false, 1, 'EHS专员', 'EHS负责人'),
  ('TOPIC_WASTE_MANAGEMENT', 'METRIC_TOTAL_WASTE', true, false, 1, 'EHS专员', 'EHS负责人'),
  ('TOPIC_WASTE_MANAGEMENT', 'METRIC_HAZARDOUS_WASTE', true, false, 2, 'EHS专员', 'EHS负责人'),
  ('TOPIC_EMPLOYMENT', 'METRIC_TOTAL_EMPLOYEES', true, true, 1, 'HR专员', 'HR负责人'),
  ('TOPIC_EMPLOYMENT', 'METRIC_EMPLOYEE_TURNOVER_RATE', true, false, 2, 'HR专员', 'HR负责人'),
  ('TOPIC_EMPLOYEE_TRAINING', 'METRIC_TRAINING_HOURS', true, false, 1, 'HR专员', 'HR负责人'),
  ('TOPIC_EMPLOYEE_TRAINING', 'METRIC_TRAINING_COVERAGE', true, false, 2, 'HR专员', 'HR负责人'),
  ('TOPIC_OCCUPATIONAL_HEALTH_SAFETY', 'METRIC_WORK_INJURY_COUNT', true, false, 1, 'EHS专员', 'EHS负责人'),
  ('TOPIC_SUPPLY_CHAIN', 'METRIC_SUPPLIER_COUNT', true, false, 1, '采购专员', '采购负责人'),
  ('TOPIC_SUPPLY_CHAIN', 'METRIC_SUPPLIER_ESG_ASSESSMENT_RATE', true, false, 2, '采购专员', '采购负责人'),
  ('TOPIC_BUSINESS_ETHICS', 'METRIC_BUSINESS_ETHICS_DESC', true, true, 1, '合规专员', '法务合规负责人'),
  ('TOPIC_CLIMATE_CHANGE', 'METRIC_ENV_MANAGEMENT_DESC', false, false, 5, 'EHS专员', 'EHS负责人')
) AS v(topic_code, metric_code, default_selected, is_required, sort_order, collector_role, reviewer_role)
JOIN esg_topics t ON t.topic_code = v.topic_code
JOIN esg_metrics m ON m.metric_code = v.metric_code
ON CONFLICT (topic_id, metric_id) DO UPDATE
SET default_selected = EXCLUDED.default_selected,
    is_required = EXCLUDED.is_required,
    sort_order = EXCLUDED.sort_order,
    recommended_collector_role = EXCLUDED.recommended_collector_role,
    recommended_reviewer_role = EXCLUDED.recommended_reviewer_role,
    status = 'active';

INSERT INTO clause_metric_maps (clause_id, metric_id, disclosure_requirement_type, standard_specific_instruction, source_required, status)
SELECT c.clause_id, m.metric_id, v.disclosure_requirement_type, v.instruction, true, 'active'
FROM (
  VALUES
  ('GRI_305_1', 'METRIC_SCOPE1_GHG', 'required', '应披露直接温室气体排放量、单位和统计边界。'),
  ('GRI_305_2', 'METRIC_SCOPE2_GHG', 'required', '应披露能源间接温室气体排放量、单位和统计边界。'),
  ('GRI_302_1', 'METRIC_TOTAL_ENERGY', 'required', '应披露组织内部能源消耗。'),
  ('GRI_303_3', 'METRIC_WATER_WITHDRAWAL', 'conditional', '水资源为重要议题时披露取水量。'),
  ('GRI_306_3', 'METRIC_TOTAL_WASTE', 'conditional', '废弃物为重要议题时披露废弃物产生量。'),
  ('GRI_403_9', 'METRIC_WORK_INJURY_COUNT', 'conditional', '职业健康安全为重要议题时披露工伤相关指标。'),
  ('GRI_404_1', 'METRIC_TRAINING_HOURS', 'conditional', '员工培训为重要议题时披露培训时长。'),
  ('IFRS_S2_GOV', 'METRIC_CLIMATE_GOVERNANCE_DESC', 'conditional', '气候相关披露中说明治理机制。'),
  ('IFRS_S2_GHG', 'METRIC_SCOPE1_GHG', 'conditional', '气候相关披露中披露范围一排放。'),
  ('IFRS_S2_GHG', 'METRIC_SCOPE2_GHG', 'conditional', '气候相关披露中披露范围二排放。'),
  ('IFRS_S2_GHG', 'METRIC_SCOPE3_GHG', 'conditional', '如适用，披露范围三排放。')
) AS v(clause_code, metric_code, disclosure_requirement_type, instruction)
JOIN standard_clauses c ON c.clause_code = v.clause_code
JOIN esg_metrics m ON m.metric_code = v.metric_code
ON CONFLICT (clause_id, metric_id) DO UPDATE
SET disclosure_requirement_type = EXCLUDED.disclosure_requirement_type,
    standard_specific_instruction = EXCLUDED.standard_specific_instruction,
    source_required = true,
    status = 'active';

-- =========================================================
-- 11. 指标校验规则
-- =========================================================

INSERT INTO metric_validation_rules (
  metric_id, validation_rule_code, rule_type, rule_name, rule_params,
  severity, block_submission, message, status
)
SELECT m.metric_id, v.validation_rule_code, v.rule_type, v.rule_name, v.rule_params::jsonb,
       v.severity::severity_level, v.block_submission, v.message, 'active'
FROM (
  VALUES
  ('METRIC_SCOPE1_GHG', 'RULE_SCOPE1_UNIT', 'unit_check', '范围一排放单位校验', '{"allowed_units":["tCO2e"]}', 'high', true, '范围一排放单位应为tCO2e。'),
  ('METRIC_SCOPE1_GHG', 'RULE_SCOPE1_YOY', 'yoy_check', '范围一排放同比校验', '{"threshold_percent":30}', 'medium', false, '范围一排放同比变化超过30%，请填写说明。'),
  ('METRIC_SCOPE2_GHG', 'RULE_SCOPE2_UNIT', 'unit_check', '范围二排放单位校验', '{"allowed_units":["tCO2e"]}', 'high', true, '范围二排放单位应为tCO2e。'),
  ('METRIC_TOTAL_ENERGY', 'RULE_ENERGY_NON_NEGATIVE', 'non_negative_check', '能源消耗非负校验', '{}', 'high', true, '能源消耗不能小于0。'),
  ('METRIC_WATER_WITHDRAWAL', 'RULE_WATER_NON_NEGATIVE', 'non_negative_check', '取水量非负校验', '{}', 'high', true, '取水量不能小于0。'),
  ('METRIC_TRAINING_COVERAGE', 'RULE_TRAINING_COVERAGE_RANGE', 'range_check', '培训覆盖率范围校验', '{"min":0,"max":100}', 'high', true, '培训覆盖率应在0%-100%之间。'),
  ('METRIC_EMPLOYEE_TURNOVER_RATE', 'RULE_TURNOVER_RANGE', 'range_check', '员工流失率范围校验', '{"min":0,"max":100}', 'high', true, '员工流失率应在0%-100%之间。'),
  ('METRIC_TOTAL_EMPLOYEES', 'RULE_EMPLOYEE_REQUIRED', 'required_check', '员工总人数必填校验', '{}', 'high', true, '员工总人数为必填项。')
) AS v(metric_code, validation_rule_code, rule_type, rule_name, rule_params, severity, block_submission, message)
JOIN esg_metrics m ON m.metric_code = v.metric_code
ON CONFLICT (validation_rule_code) DO UPDATE
SET rule_type = EXCLUDED.rule_type,
    rule_name = EXCLUDED.rule_name,
    rule_params = EXCLUDED.rule_params,
    severity = EXCLUDED.severity,
    block_submission = EXCLUDED.block_submission,
    message = EXCLUDED.message,
    status = 'active';

-- =========================================================
-- 12. 证据要求
-- =========================================================

INSERT INTO evidence_requirements (
  tenant_id, target_type, target_code, evidence_type, evidence_name,
  is_required, file_format, description, status
)
SELECT NULL, v.target_type, v.target_code, v.evidence_type, v.evidence_name,
       v.is_required, v.file_format, v.description, 'active'
FROM (
  VALUES
  ('metric', 'METRIC_SCOPE1_GHG', 'calculation_sheet', '范围一温室气体排放核算表', true, ARRAY['xlsx','pdf'], '请上传范围一排放核算过程文件。'),
  ('metric', 'METRIC_SCOPE2_GHG', 'calculation_sheet', '范围二温室气体排放核算表', true, ARRAY['xlsx','pdf'], '请上传范围二排放核算过程文件。'),
  ('metric', 'METRIC_TOTAL_ENERGY', 'calculation_sheet', '能源消耗统计表', false, ARRAY['xlsx','pdf'], '请上传能源消耗统计表或能源系统导出文件。'),
  ('metric', 'METRIC_WATER_WITHDRAWAL', 'invoice_or_bill', '水资源统计或水费账单', false, ARRAY['xlsx','pdf'], '请上传水资源统计表或水费账单。'),
  ('metric', 'METRIC_TOTAL_EMPLOYEES', 'calculation_sheet', '员工人数统计表', true, ARRAY['xlsx','pdf'], '请上传员工人数统计表。'),
  ('metric', 'METRIC_TRAINING_HOURS', 'training_record', '培训记录表', false, ARRAY['xlsx','pdf'], '请上传培训记录表。'),
  ('topic', 'TOPIC_BUSINESS_ETHICS', 'policy_document', '商业道德与合规制度', false, ARRAY['pdf','docx'], '请上传商业道德、反腐败或合规相关制度。'),
  ('topic', 'TOPIC_SUPPLY_CHAIN', 'policy_document', '供应商管理制度', false, ARRAY['pdf','docx'], '请上传供应商准入、评估或管理制度。')
) AS v(target_type, target_code, evidence_type, evidence_name, is_required, file_format, description)
ON CONFLICT DO NOTHING;

-- =========================================================
-- 13. 议题别名、指标别名
-- =========================================================

INSERT INTO topic_aliases (topic_id, alias_name, language, source_type, match_priority, status)
SELECT t.topic_id, v.alias_name, 'zh', v.source_type, v.match_priority, 'active'
FROM (
  VALUES
  ('TOPIC_GHG_EMISSIONS', '碳排放管理', 'manual', 'high'),
  ('TOPIC_GHG_EMISSIONS', '温室气体管理', 'manual', 'high'),
  ('TOPIC_GHG_EMISSIONS', '碳排放', 'manual', 'high'),
  ('TOPIC_CLIMATE_CHANGE', '应对气候变化', 'manual', 'high'),
  ('TOPIC_CLIMATE_CHANGE', '气候风险管理', 'manual', 'medium'),
  ('TOPIC_ENERGY_MANAGEMENT', '绿色运营', 'manual', 'medium'),
  ('TOPIC_ENERGY_MANAGEMENT', '节能管理', 'manual', 'high'),
  ('TOPIC_WATER_MANAGEMENT', '水资源利用', 'manual', 'high'),
  ('TOPIC_WASTE_MANAGEMENT', '固废管理', 'manual', 'medium'),
  ('TOPIC_EMPLOYEE_TRAINING', '员工发展', 'manual', 'high'),
  ('TOPIC_OCCUPATIONAL_HEALTH_SAFETY', '安全生产', 'manual', 'high'),
  ('TOPIC_SUPPLY_CHAIN', '责任采购', 'manual', 'high'),
  ('TOPIC_BUSINESS_ETHICS', '反腐败与商业道德', 'manual', 'high')
) AS v(topic_code, alias_name, source_type, match_priority)
JOIN esg_topics t ON t.topic_code = v.topic_code
ON CONFLICT (topic_id, alias_name, language) DO UPDATE
SET source_type = EXCLUDED.source_type,
    match_priority = EXCLUDED.match_priority,
    status = 'active';

INSERT INTO metric_aliases (metric_id, alias_name, language, source_type, match_priority, status)
SELECT m.metric_id, v.alias_name, 'zh', v.source_type, v.match_priority, 'active'
FROM (
  VALUES
  ('METRIC_SCOPE1_GHG', '直接温室气体排放', 'manual', 'high'),
  ('METRIC_SCOPE1_GHG', '范围1排放', 'manual', 'high'),
  ('METRIC_SCOPE2_GHG', '能源间接温室气体排放', 'manual', 'high'),
  ('METRIC_SCOPE2_GHG', '范围2排放', 'manual', 'high'),
  ('METRIC_SCOPE3_GHG', '其他间接温室气体排放', 'manual', 'medium'),
  ('METRIC_TOTAL_ENERGY', '综合能耗', 'manual', 'high'),
  ('METRIC_ELECTRICITY_CONSUMPTION', '总用电量', 'manual', 'high'),
  ('METRIC_WATER_WITHDRAWAL', '总取水量', 'manual', 'high'),
  ('METRIC_TOTAL_WASTE', '废弃物总量', 'manual', 'medium'),
  ('METRIC_TRAINING_HOURS', '培训小时数', 'manual', 'high'),
  ('METRIC_TRAINING_COVERAGE', '培训覆盖比例', 'manual', 'medium')
) AS v(metric_code, alias_name, source_type, match_priority)
JOIN esg_metrics m ON m.metric_code = v.metric_code
ON CONFLICT (metric_id, alias_name, language) DO UPDATE
SET source_type = EXCLUDED.source_type,
    match_priority = EXCLUDED.match_priority,
    status = 'active';

-- =========================================================
-- 14. 常见负责部门规则
-- =========================================================

INSERT INTO owner_rules (
  tenant_id, target_type, target_code, recommended_owner_department,
  recommended_collaborator_departments, recommended_collector_role,
  recommended_reviewer_role, recommendation_reason, status
)
SELECT NULL, v.target_type, v.target_code, v.owner_dept, v.collab_depts,
       v.collector_role, v.reviewer_role, v.reason, 'active'
FROM (
  VALUES
  ('topic', 'TOPIC_GHG_EMISSIONS', 'EHS部门', ARRAY['生产部','财务部'], 'EHS专员', 'EHS负责人', '温室气体排放数据通常由EHS部门统计。'),
  ('topic', 'TOPIC_CLIMATE_CHANGE', 'EHS部门', ARRAY['战略部','财务部'], 'EHS专员', 'EHS负责人', '气候相关信息通常由EHS牵头，相关部门协作。'),
  ('topic', 'TOPIC_ENERGY_MANAGEMENT', 'EHS部门', ARRAY['生产部','财务部'], 'EHS专员', 'EHS负责人', '能源数据通常由EHS或生产部门统计。'),
  ('topic', 'TOPIC_EMPLOYEE_TRAINING', '人力资源部', ARRAY[]::text[], 'HR专员', 'HR负责人', '员工培训数据通常由人力资源部管理。'),
  ('topic', 'TOPIC_EMPLOYMENT', '人力资源部', ARRAY[]::text[], 'HR专员', 'HR负责人', '员工雇佣数据通常由人力资源部管理。'),
  ('topic', 'TOPIC_OCCUPATIONAL_HEALTH_SAFETY', 'EHS部门', ARRAY['生产部'], 'EHS专员', 'EHS负责人', '职业健康安全通常由EHS部门负责。'),
  ('topic', 'TOPIC_SUPPLY_CHAIN', '采购部', ARRAY['法务合规部'], '采购专员', '采购负责人', '供应链管理通常由采购部门负责。'),
  ('topic', 'TOPIC_BUSINESS_ETHICS', '法务合规部', ARRAY['人力资源部'], '合规专员', '法务合规负责人', '商业道德与合规通常由法务合规部门负责。'),
  ('topic', 'TOPIC_CORPORATE_GOVERNANCE', '董秘办', ARRAY['法务合规部'], '董秘办专员', '董秘办负责人', '公司治理信息通常由董秘办负责。')
) AS v(target_type, target_code, owner_dept, collab_depts, collector_role, reviewer_role, reason)
ON CONFLICT DO NOTHING;

-- =========================================================
-- 15. 行业适用性示例
-- =========================================================

INSERT INTO industry_applicability (target_type, target_code, gics_level, gics_code, applicability_level, description, status)
VALUES
  ('topic', 'TOPIC_GHG_EMISSIONS', 2, '2010', 'high', '资本货物行业通常适用温室气体排放披露。', 'active'),
  ('topic', 'TOPIC_ENERGY_MANAGEMENT', 2, '2010', 'high', '工业企业通常涉及能源管理。', 'active'),
  ('topic', 'TOPIC_WATER_MANAGEMENT', 4, '15101050', 'high', '化工行业通常涉及水资源管理。', 'active'),
  ('topic', 'TOPIC_SUPPLY_CHAIN', 3, '452030', 'high', '电子设备行业通常关注供应链管理。', 'active')
ON CONFLICT DO NOTHING;

-- =========================================================
-- 16. AI模型配置示例
-- =========================================================

INSERT INTO ai_models (
  tenant_id, provider, model_name, enabled, capabilities,
  input_price_per_1k_tokens, output_price_per_1k_tokens, is_default, settings
)
SELECT t.tenant_id, 'configurable_provider', 'high_capability_model', true,
       ARRAY['document_parse','topic_extraction','chapter_writing','chapter_review','full_review'],
       0.00000000, 0.00000000, true,
       '{"note":"请在部署环境中替换真实模型供应商、模型名称和价格"}'::jsonb
FROM tenants t
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT DO NOTHING;

INSERT INTO ai_models (
  tenant_id, provider, model_name, enabled, capabilities,
  input_price_per_1k_tokens, output_price_per_1k_tokens, is_default, settings
)
SELECT t.tenant_id, 'configurable_provider', 'low_cost_model', true,
       ARRAY['classification','format_fix','summary','validation_explanation'],
       0.00000000, 0.00000000, false,
       '{"note":"用于低成本分类、摘要、格式修复和校验解释"}'::jsonb
FROM tenants t
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT DO NOTHING;

-- =========================================================
-- 17. 示例报告项目
-- =========================================================

INSERT INTO report_projects (
  tenant_id, enterprise_id, project_name, report_year, report_type, report_language,
  reporting_period_start, reporting_period_end, report_boundary,
  selected_standard_codes, project_owner_user_id, project_status, created_by
)
SELECT t.tenant_id, e.enterprise_id, '示例股份2025年度ESG报告项目', 2025, 'ESG', 'zh',
       '2025-01-01'::date, '2025-12-31'::date, '集团及下属子公司',
       ARRAY['STD_GRI','STD_IFRS_S2','STD_SSE_SUSTAINABILITY'],
       owner.user_id, 'draft', owner.user_id
FROM tenants t
JOIN enterprises e ON e.tenant_id = t.tenant_id AND e.enterprise_code = 'ENT_DEMO'
LEFT JOIN users owner ON owner.tenant_id = t.tenant_id AND owner.email = 'project.owner@example.com'
WHERE t.tenant_code = 'DEFAULT'
ON CONFLICT (tenant_id, enterprise_id, report_year, project_name) DO UPDATE
SET selected_standard_codes = EXCLUDED.selected_standard_codes,
    project_owner_user_id = EXCLUDED.project_owner_user_id,
    updated_at = now();

-- 企业访问权限
INSERT INTO enterprise_user_access (tenant_id, enterprise_id, user_id, access_scope, status)
SELECT t.tenant_id, e.enterprise_id, u.user_id, 'all', 'active'
FROM tenants t
JOIN enterprises e ON e.tenant_id = t.tenant_id AND e.enterprise_code = 'ENT_DEMO'
JOIN users u ON u.tenant_id = t.tenant_id
WHERE t.tenant_code = 'DEFAULT'
  AND u.email IN (
    'admin@example.com',
    'project.owner@example.com',
    'esg.expert@example.com',
    'ehs.collector@example.com',
    'ehs.reviewer@example.com',
    'hr.collector@example.com',
    'hr.reviewer@example.com'
  )
ON CONFLICT (enterprise_id, user_id) DO UPDATE
SET access_scope = 'all',
    status = 'active';

-- =========================================================
-- 18. 种子数据完成标记
-- =========================================================

INSERT INTO audit_logs (
  tenant_id, action_type, object_type, description, after_payload, created_at
)
SELECT t.tenant_id, 'seed_data_loaded', 'database_seed',
       'ESG数据库种子数据v0.1已加载',
       '{"seed_version":"v0.1"}'::jsonb,
       now()
FROM tenants t
WHERE t.tenant_code = 'DEFAULT';

COMMIT;

-- =========================================================
-- 19. 快速验证SQL
-- =========================================================

-- SELECT tenant_code, tenant_name FROM esg.tenants;
-- SELECT role_code, role_name FROM esg.roles ORDER BY role_code;
-- SELECT standard_code, standard_short_name FROM esg.esg_standards ORDER BY standard_code;
-- SELECT topic_code, topic_name, topic_category FROM esg.esg_topics ORDER BY topic_code;
-- SELECT metric_code, metric_name, metric_type, default_unit FROM esg.esg_metrics ORDER BY metric_code;
-- SELECT project_name, report_year, project_status FROM esg.report_projects;
