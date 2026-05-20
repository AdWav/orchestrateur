-- Builder catalog: palette de briques, versions, composition, custom, audit.
-- Renommage validé: ref_bricks -> builder_bricks (préfixe builder_* sur tout le module).

-- ---------------------------------------------------------------------------
-- Référentiel
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS builder_domains (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(64) NOT NULL,
    label VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_domains_code (code)
);

CREATE TABLE IF NOT EXISTS builder_brick_types (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(64) NOT NULL,
    label VARCHAR(255) NOT NULL,
    UNIQUE KEY uq_builder_brick_types_code (code)
);

CREATE TABLE IF NOT EXISTS builder_bricks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    type_id BIGINT UNSIGNED NOT NULL,
    domain_id BIGINT UNSIGNED NULL,
    slug VARCHAR(128) NOT NULL,
    label VARCHAR(255) NOT NULL,
    description TEXT NULL,
    metadata JSON NOT NULL DEFAULT (JSON_OBJECT()),
    status ENUM('official', 'deprecated', 'draft_catalog') NOT NULL DEFAULT 'official',
    source ENUM('catalog_seed', 'human', 'promoted', 'llm_merged') NOT NULL DEFAULT 'catalog_seed',
    parent_brick_id BIGINT UNSIGNED NULL,
    created_by VARCHAR(128) NOT NULL DEFAULT 'system:seeder',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_bricks_type_slug (type_id, slug),
    CONSTRAINT fk_builder_bricks_type FOREIGN KEY (type_id) REFERENCES builder_brick_types (id),
    CONSTRAINT fk_builder_bricks_domain FOREIGN KEY (domain_id) REFERENCES builder_domains (id),
    CONSTRAINT fk_builder_bricks_parent FOREIGN KEY (parent_brick_id) REFERENCES builder_bricks (id)
);

CREATE TABLE IF NOT EXISTS builder_brick_versions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    brick_id BIGINT UNSIGNED NOT NULL,
    version VARCHAR(32) NOT NULL,
    status ENUM('published', 'archived') NOT NULL DEFAULT 'published',
    changelog TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_brick_versions (brick_id, version),
    CONSTRAINT fk_builder_brick_versions_brick FOREIGN KEY (brick_id) REFERENCES builder_bricks (id) ON DELETE CASCADE,
    CONSTRAINT chk_builder_brick_version_format CHECK (version REGEXP '^[0-9]+\\.[0-9]+\\.[0-9]+$')
);

CREATE TABLE IF NOT EXISTS builder_brick_actions (
    brick_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    facet_operational VARCHAR(255) NULL,
    facet_capability VARCHAR(255) NULL,
    facet_deliverable VARCHAR(255) NULL,
    CONSTRAINT fk_builder_brick_actions_brick FOREIGN KEY (brick_id) REFERENCES builder_bricks (id) ON DELETE CASCADE,
    CONSTRAINT chk_builder_brick_actions_facets CHECK (
        facet_operational IS NOT NULL
        OR facet_capability IS NOT NULL
        OR facet_deliverable IS NOT NULL
    )
);

CREATE TABLE IF NOT EXISTS builder_limit_templates (
    brick_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    limit_family ENUM('text', 'execution', 'tools', 'repo') NOT NULL,
    parameters_schema JSON NOT NULL DEFAULT (JSON_OBJECT()),
    parameters_default JSON NOT NULL DEFAULT (JSON_OBJECT()),
    CONSTRAINT fk_builder_limit_templates_brick FOREIGN KEY (brick_id) REFERENCES builder_bricks (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS builder_frameworks (
    brick_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
    framework_kind ENUM(
        'methodology',
        'work_context',
        'constraint_set',
        'quality_frame',
        'workflow_pattern'
    ) NOT NULL,
    template_payload JSON NOT NULL DEFAULT (JSON_OBJECT()),
    CONSTRAINT fk_builder_frameworks_brick FOREIGN KEY (brick_id) REFERENCES builder_bricks (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS builder_runner_bindings (
    runner_role VARCHAR(128) NOT NULL PRIMARY KEY,
    label VARCHAR(255) NOT NULL,
    implementation_kind ENUM('specialist', 'catalog_generic') NOT NULL DEFAULT 'specialist',
    is_available TINYINT(1) NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------------
-- Pending (granularité champ)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS builder_composition_sessions (
    id CHAR(36) NOT NULL PRIMARY KEY,
    kind ENUM('agent', 'workflow', 'brick') NOT NULL,
    actor_type ENUM('human', 'llm', 'system') NOT NULL,
    actor_id VARCHAR(128) NOT NULL,
    goal_prompt TEXT NULL,
    metadata JSON NOT NULL DEFAULT (JSON_OBJECT()),
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS builder_pending_brick_proposals (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id CHAR(36) NULL,
    proposed_by ENUM('llm', 'human') NOT NULL DEFAULT 'llm',
    target_brick_id BIGINT UNSIGNED NULL,
    proposed_type_id BIGINT UNSIGNED NULL,
    field_path VARCHAR(255) NOT NULL,
    proposed_value JSON NOT NULL,
    previous_value JSON NULL,
    status ENUM('pending', 'approved', 'rejected', 'superseded') NOT NULL DEFAULT 'pending',
    merged_brick_id BIGINT UNSIGNED NULL,
    merged_version VARCHAR(32) NULL,
    reviewed_by VARCHAR(128) NULL,
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_builder_pending_brick_session FOREIGN KEY (session_id) REFERENCES builder_composition_sessions (id),
    CONSTRAINT fk_builder_pending_brick_target FOREIGN KEY (target_brick_id) REFERENCES builder_bricks (id),
    CONSTRAINT fk_builder_pending_brick_type FOREIGN KEY (proposed_type_id) REFERENCES builder_brick_types (id),
    CONSTRAINT fk_builder_pending_brick_merged FOREIGN KEY (merged_brick_id) REFERENCES builder_bricks (id),
    KEY idx_builder_pending_brick_status (status, proposed_by),
    KEY idx_builder_pending_brick_session (session_id)
);

-- ---------------------------------------------------------------------------
-- Agents catalogue (ex-catalog_agents -> builder_agents)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS builder_agents (
    id VARCHAR(255) NOT NULL PRIMARY KEY,
    domain_id BIGINT UNSIGNED NULL,
    published_version_id BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_builder_agents_domain FOREIGN KEY (domain_id) REFERENCES builder_domains (id)
);

CREATE TABLE IF NOT EXISTS builder_agent_versions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    version VARCHAR(32) NOT NULL,
    status ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
    payload JSON NOT NULL,
    runner_role VARCHAR(128) NULL,
    default_runner VARCHAR(128) NOT NULL DEFAULT 'catalog_generic',
    changelog TEXT NULL,
    published_at TIMESTAMP NULL,
    published_by VARCHAR(128) NULL,
    created_by VARCHAR(128) NOT NULL DEFAULT 'system:seeder',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_agent_versions (agent_id, version),
    KEY idx_builder_agent_versions_status (agent_id, status),
    CONSTRAINT fk_builder_agent_versions_agent FOREIGN KEY (agent_id) REFERENCES builder_agents (id) ON DELETE CASCADE,
    CONSTRAINT chk_builder_agent_version_format CHECK (version REGEXP '^[0-9]+\\.[0-9]+\\.[0-9]+$')
);

ALTER TABLE builder_agents
    ADD CONSTRAINT fk_builder_agents_published_version
    FOREIGN KEY (published_version_id) REFERENCES builder_agent_versions (id);

CREATE TABLE IF NOT EXISTS builder_agent_composition (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    version_id BIGINT UNSIGNED NOT NULL,
    brick_id BIGINT UNSIGNED NOT NULL,
    slot ENUM(
        'role',
        'capability',
        'input',
        'output',
        'guardrail',
        'limit',
        'framework'
    ) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    override_text TEXT NULL,
    UNIQUE KEY uq_builder_agent_composition (version_id, slot, sort_order),
    CONSTRAINT fk_builder_agent_composition_version FOREIGN KEY (version_id) REFERENCES builder_agent_versions (id) ON DELETE CASCADE,
    CONSTRAINT fk_builder_agent_composition_brick FOREIGN KEY (brick_id) REFERENCES builder_bricks (id)
);

CREATE TABLE IF NOT EXISTS builder_pending_agent_field_proposals (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    draft_version_id BIGINT UNSIGNED NOT NULL,
    field_path VARCHAR(255) NOT NULL,
    proposed_value JSON NOT NULL,
    previous_value JSON NULL,
    status ENUM('pending', 'approved', 'rejected', 'superseded') NOT NULL DEFAULT 'pending',
    session_id CHAR(36) NULL,
    proposed_by ENUM('llm', 'human') NOT NULL DEFAULT 'llm',
    reviewed_by VARCHAR(128) NULL,
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_builder_pending_agent_version FOREIGN KEY (draft_version_id) REFERENCES builder_agent_versions (id) ON DELETE CASCADE,
    CONSTRAINT fk_builder_pending_agent_session FOREIGN KEY (session_id) REFERENCES builder_composition_sessions (id),
    KEY idx_builder_pending_agent_draft (draft_version_id, field_path, status)
);

-- ---------------------------------------------------------------------------
-- Workflows catalogue
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS builder_workflows (
    id VARCHAR(255) NOT NULL PRIMARY KEY,
    domain_id BIGINT UNSIGNED NULL,
    published_version_id BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_builder_workflows_domain FOREIGN KEY (domain_id) REFERENCES builder_domains (id)
);

CREATE TABLE IF NOT EXISTS builder_workflow_versions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    version VARCHAR(32) NOT NULL,
    status ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
    payload JSON NOT NULL,
    changelog TEXT NULL,
    published_at TIMESTAMP NULL,
    published_by VARCHAR(128) NULL,
    created_by VARCHAR(128) NOT NULL DEFAULT 'system:seeder',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_workflow_versions (workflow_id, version),
    KEY idx_builder_workflow_versions_status (workflow_id, status),
    CONSTRAINT fk_builder_workflow_versions_workflow FOREIGN KEY (workflow_id) REFERENCES builder_workflows (id) ON DELETE CASCADE,
    CONSTRAINT chk_builder_workflow_version_format CHECK (version REGEXP '^[0-9]+\\.[0-9]+\\.[0-9]+$')
);

ALTER TABLE builder_workflows
    ADD CONSTRAINT fk_builder_workflows_published_version
    FOREIGN KEY (published_version_id) REFERENCES builder_workflow_versions (id);

CREATE TABLE IF NOT EXISTS builder_workflow_steps (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    version_id BIGINT UNSIGNED NOT NULL,
    step_id VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    objective TEXT NOT NULL,
    agent_definition_id VARCHAR(255) NOT NULL,
    agent_source ENUM('catalog', 'custom') NOT NULL DEFAULT 'catalog',
    runner_role_override VARCHAR(128) NULL,
    depends_on_explicit JSON NOT NULL DEFAULT (JSON_ARRAY()),
    depends_on_inferred JSON NOT NULL DEFAULT (JSON_ARRAY()),
    depends_on_merged JSON NOT NULL DEFAULT (JSON_ARRAY()),
    depends_on_source ENUM('explicit', 'inferred', 'hybrid') NOT NULL DEFAULT 'explicit',
    sort_order INT NOT NULL DEFAULT 0,
    pattern_origin_step_id VARCHAR(128) NULL,
    UNIQUE KEY uq_builder_workflow_steps (version_id, step_id),
    CONSTRAINT fk_builder_workflow_steps_version FOREIGN KEY (version_id) REFERENCES builder_workflow_versions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS builder_workflow_frameworks (
    version_id BIGINT UNSIGNED NOT NULL,
    framework_brick_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (version_id, framework_brick_id),
    CONSTRAINT fk_builder_workflow_frameworks_version FOREIGN KEY (version_id) REFERENCES builder_workflow_versions (id) ON DELETE CASCADE,
    CONSTRAINT fk_builder_workflow_frameworks_brick FOREIGN KEY (framework_brick_id) REFERENCES builder_bricks (id)
);

CREATE TABLE IF NOT EXISTS builder_workflow_patterns (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(128) NOT NULL,
    domain_id BIGINT UNSIGNED NULL,
    label VARCHAR(255) NOT NULL,
    is_optional TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uq_builder_workflow_patterns_code (code),
    CONSTRAINT fk_builder_workflow_patterns_domain FOREIGN KEY (domain_id) REFERENCES builder_domains (id)
);

CREATE TABLE IF NOT EXISTS builder_workflow_pattern_steps (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    pattern_id BIGINT UNSIGNED NOT NULL,
    step_template JSON NOT NULL,
    suggested_agent_id VARCHAR(255) NULL,
    default_depends_on JSON NOT NULL DEFAULT (JSON_ARRAY()),
    sort_order INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_builder_workflow_pattern_steps_pattern FOREIGN KEY (pattern_id) REFERENCES builder_workflow_patterns (id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------------
-- Custom + promotion (v1)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS builder_custom_agents (
    id CHAR(36) NOT NULL PRIMARY KEY,
    workspace_id VARCHAR(128) NULL,
    owner_user_id VARCHAR(128) NOT NULL,
    slug VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_builder_custom_agents_owner (owner_user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS builder_custom_agent_versions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    custom_agent_id CHAR(36) NOT NULL,
    version VARCHAR(32) NOT NULL,
    status ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
    payload JSON NOT NULL,
    runner_role VARCHAR(128) NULL,
    default_runner VARCHAR(128) NOT NULL DEFAULT 'catalog_generic',
    promotion_status ENUM('private', 'submitted', 'promoted') NOT NULL DEFAULT 'private',
    changelog TEXT NULL,
    created_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_custom_agent_versions (custom_agent_id, version),
    CONSTRAINT fk_builder_custom_agent_versions_agent FOREIGN KEY (custom_agent_id) REFERENCES builder_custom_agents (id) ON DELETE CASCADE,
    CONSTRAINT chk_builder_custom_agent_version_format CHECK (version REGEXP '^[0-9]+\\.[0-9]+\\.[0-9]+$')
);

CREATE TABLE IF NOT EXISTS builder_custom_agent_composition (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    version_id BIGINT UNSIGNED NOT NULL,
    brick_id BIGINT UNSIGNED NOT NULL,
    slot ENUM(
        'role',
        'capability',
        'input',
        'output',
        'guardrail',
        'limit',
        'framework'
    ) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    override_text TEXT NULL,
    UNIQUE KEY uq_builder_custom_agent_composition (version_id, slot, sort_order),
    CONSTRAINT fk_builder_custom_agent_composition_version FOREIGN KEY (version_id) REFERENCES builder_custom_agent_versions (id) ON DELETE CASCADE,
    CONSTRAINT fk_builder_custom_agent_composition_brick FOREIGN KEY (brick_id) REFERENCES builder_bricks (id)
);

CREATE TABLE IF NOT EXISTS builder_custom_workflows (
    id CHAR(36) NOT NULL PRIMARY KEY,
    workspace_id VARCHAR(128) NULL,
    owner_user_id VARCHAR(128) NOT NULL,
    slug VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS builder_custom_workflow_versions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    custom_workflow_id CHAR(36) NOT NULL,
    version VARCHAR(32) NOT NULL,
    status ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
    payload JSON NOT NULL,
    promotion_status ENUM('private', 'submitted', 'promoted') NOT NULL DEFAULT 'private',
    created_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_builder_custom_workflow_versions (custom_workflow_id, version),
    CONSTRAINT fk_builder_custom_workflow_versions FOREIGN KEY (custom_workflow_id) REFERENCES builder_custom_workflows (id) ON DELETE CASCADE,
    CONSTRAINT chk_builder_custom_workflow_version_format CHECK (version REGEXP '^[0-9]+\\.[0-9]+\\.[0-9]+$')
);

CREATE TABLE IF NOT EXISTS builder_custom_workflow_steps (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    version_id BIGINT UNSIGNED NOT NULL,
    step_id VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    objective TEXT NOT NULL,
    agent_definition_id VARCHAR(255) NOT NULL,
    agent_source ENUM('catalog', 'custom') NOT NULL DEFAULT 'catalog',
    depends_on_explicit JSON NOT NULL DEFAULT (JSON_ARRAY()),
    depends_on_inferred JSON NOT NULL DEFAULT (JSON_ARRAY()),
    depends_on_merged JSON NOT NULL DEFAULT (JSON_ARRAY()),
    depends_on_source ENUM('explicit', 'inferred', 'hybrid') NOT NULL DEFAULT 'explicit',
    sort_order INT NOT NULL DEFAULT 0,
    UNIQUE KEY uq_builder_custom_workflow_steps (version_id, step_id),
    CONSTRAINT fk_builder_custom_workflow_steps_version FOREIGN KEY (version_id) REFERENCES builder_custom_workflow_versions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS builder_promotion_requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    requester_id VARCHAR(128) NOT NULL,
    source_kind ENUM(
        'custom_agent',
        'custom_workflow',
        'custom_brick_set',
        'pending_brick_batch'
    ) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    target_kind ENUM('builder_brick', 'builder_agent', 'builder_workflow') NOT NULL,
    target_id VARCHAR(255) NULL,
    proposed_payload JSON NOT NULL,
    status ENUM('submitted', 'in_review', 'approved', 'rejected') NOT NULL DEFAULT 'submitted',
    reviewer_id VARCHAR(128) NULL,
    review_notes TEXT NULL,
    result_catalog_version_id BIGINT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    KEY idx_builder_promotion_requests_status (status, created_at)
);

-- ---------------------------------------------------------------------------
-- Sessions & audit
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS builder_composition_session_inputs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id CHAR(36) NOT NULL,
    ref_kind ENUM(
        'brick',
        'builder_agent',
        'builder_workflow',
        'pattern',
        'file_catalog'
    ) NOT NULL,
    ref_id VARCHAR(255) NOT NULL,
    CONSTRAINT fk_builder_session_inputs_session FOREIGN KEY (session_id) REFERENCES builder_composition_sessions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS builder_composition_session_outputs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id CHAR(36) NOT NULL,
    entity_kind ENUM('builder_agent_version', 'builder_workflow_version', 'brick') NOT NULL,
    entity_version_id BIGINT UNSIGNED NOT NULL,
    draft_payload JSON NULL,
    CONSTRAINT fk_builder_session_outputs_session FOREIGN KEY (session_id) REFERENCES builder_composition_sessions (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS builder_audit_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id CHAR(36) NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_version VARCHAR(32) NULL,
    action VARCHAR(64) NOT NULL,
    actor_type ENUM('human', 'llm', 'system') NOT NULL,
    actor_id VARCHAR(128) NOT NULL,
    before_payload JSON NULL,
    after_payload JSON NULL,
    correlation_id CHAR(36) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_builder_audit_session FOREIGN KEY (session_id) REFERENCES builder_composition_sessions (id),
    KEY idx_builder_audit_entity (entity_type, entity_id, created_at),
    KEY idx_builder_audit_session (session_id),
    KEY idx_builder_audit_actor (actor_type, actor_id, created_at)
);

-- ---------------------------------------------------------------------------
-- Seed lookup (types & domaines)
-- ---------------------------------------------------------------------------

INSERT INTO builder_domains (code, label) VALUES
    ('dev', 'Developpement'),
    ('doc', 'Documentation'),
    ('viz', 'Visualisation'),
    ('refactor', 'Refactoring et qualite'),
    ('audit', 'Audit'),
    ('deal', 'Deal review')
ON DUPLICATE KEY UPDATE label = VALUES(label);

INSERT INTO builder_brick_types (code, label) VALUES
    ('role', 'Role metier'),
    ('capability', 'Capacite'),
    ('input', 'Entree'),
    ('output', 'Sortie'),
    ('guardrail', 'Garde-fou'),
    ('limit', 'Limite'),
    ('framework', 'Cadre'),
    ('action', 'Action'),
    ('pattern_step', 'Etape de pattern')
ON DUPLICATE KEY UPDATE label = VALUES(label);
