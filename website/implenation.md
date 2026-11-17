# Tigray Medical Association -- Digital Health Initiative

## Platform Architecture and PostgreSQL Database Design

## 1. Platform vision

The platform will connect healthcare professionals, technologists,
researchers, academics, innovators, institutions, and communities to
advance healthcare through digital innovation, technology, research, and
collaboration in Tigray.

**Guiding statement:** Connecting people, knowledge, technology, and
innovation to transform healthcare in Tigray.

The platform has three connected areas:

1.  **Public institutional website** -- presents the initiative, its
    people, focus areas, projects, datasets, products, research, events,
    resources, partnerships, and opportunities.
2.  **Members' collaboration portal** -- provides approved members with
    a secure space to collaborate on projects, communities, datasets,
    products, and research.
3.  **Administrative workspace** -- supports membership review, content
    governance, approvals, user and role management, and platform
    oversight.

## 2. Public website

Suggested navigation:

-   Home
-   About Us
-   Our Team
-   Focus Areas
-   Projects
-   Datasets
-   Products
-   Research and Publications
-   News and Events
-   Resources
-   Organizations and Partnerships
-   Opportunities
-   Get Involved
-   Contact Us

Public visitors may browse content that has been approved and marked
public. They may submit inquiries and membership applications, but they
cannot participate in members-only collaboration.

## 3. Members' collaboration portal

Only approved, active initiative members may participate in internal
collaboration.

Core modules:

-   Member login and dashboard
-   Professional profiles and member directory
-   Communities of Practice
-   Project teams and collaboration spaces
-   Dataset submissions, curation, and version management
-   Product proposals and development teams
-   Research collaboration and publications
-   Internal discussions and comments
-   Events, opportunities, and notifications

A healthcare beneficiary may use a deployed public-facing health product
without becoming a member of the initiative's internal collaboration
portal.

## 4. Administrative workspace

Administrative capabilities:

-   Review and approve membership applications
-   Manage member status and membership types
-   Manage public website content
-   Review and approve projects
-   Review datasets, metadata, versions, and access requests
-   Review products before public listing
-   Manage global roles and permissions
-   Manage organizations and partnerships
-   View audit logs and platform analytics

## 5. Main user categories

1.  **Public visitors:** browse approved public information, submit
    inquiries, and apply for membership.
2.  **Approved members:** healthcare professionals, researchers,
    academics, technologists, students, and innovators who collaborate
    within the platform.
3.  **Initiative leadership:** chairperson, executive committee, and
    coordinators responsible for governance and approvals.
4.  **Dataset contributors and curators:** submit, document, validate,
    and maintain datasets.
5.  **Project and product teams:** propose and develop projects and
    products.
6.  **Research collaborators:** coordinate research and publications.
7.  **Institutional and development partners:** hospitals, health
    bureaus, NGOs, universities, companies, and development
    organizations.
8.  **Healthcare beneficiaries:** people and communities who may use
    deployed health services and products.

One person may hold several professional or project roles. A person's
professional identity should be distinct from their system permissions.
Project-specific authority should be scoped to the relevant project
rather than granting global administrative access.

## 6. Membership and collaboration policy

The selected model is **members-only internal collaboration**.

-   Only approved and active members may join internal projects and
    communities.
-   Only approved and active members may contribute datasets and
    products or participate in internal research and discussions.
-   Public visitors can access only content explicitly marked public.
-   External professionals may apply for membership, but they do not
    receive internal collaboration access merely by registering or
    visiting the website.
-   Membership approval, account activation, and resource-level
    permissions are separate checks.

## 7. Suggested technology stack

  -----------------------------------------------------------------------
  Layer                               Technology
  ----------------------------------- -----------------------------------
  Frontend                            Next.js and TypeScript

  UI styling                          Tailwind CSS

  Backend API                         Python and FastAPI

  Database                            PostgreSQL

  ORM                                 SQLAlchemy

  Database migrations                 Alembic

  Authentication                      Secure server-side sessions or
                                      token-based authentication

  File storage                        S3-compatible object storage

  API documentation                   OpenAPI / Swagger
  -----------------------------------------------------------------------

## 8. Relational database design

### 8.1 Identity and membership

#### `persons`

Stores a person's professional identity and profile.

-   `person_id` -- UUID primary key
-   `full_name`
-   `professional_title`
-   `biography`
-   `phone`
-   `location`
-   `profile_photo_url`
-   `profile_visibility` -- `public`, `members`, or `private`
-   `created_at`
-   `updated_at`

#### `user_accounts`

Stores authentication and account status. A person may have at most one
account.

-   `user_account_id` -- UUID primary key
-   `person_id` -- unique foreign key to `persons`
-   `email`
-   `password_hash`
-   `account_status` -- `pending`, `active`, `suspended`, or `disabled`
-   `email_verified_at`
-   `last_login_at`
-   `created_at`

#### `membership_types`

Defines available membership categories.

-   `membership_type_id` -- UUID primary key
-   `name` -- unique
-   `description`
-   `is_active`

#### `memberships`

Stores the person's current membership record.

-   `membership_id` -- UUID primary key
-   `person_id` -- unique foreign key to `persons`
-   `membership_type_id` -- foreign key to `membership_types`
-   `status` -- `pending`, `approved`, `rejected`, `suspended`,
    `expired`, or `revoked`
-   `applied_at`
-   `reviewed_by` -- foreign key to `persons`
-   `reviewed_at`
-   `expiry_date`

For a production system, keep a separate membership application/review
history table if people may reapply or if every decision must be
retained.

### 8.2 Roles and permissions

#### `roles`

Global system roles, such as member, administrator, or content manager.

-   `role_id` -- UUID primary key
-   `name` -- unique
-   `description`

#### `permissions`

Individual permissions, such as approving memberships or publishing
datasets.

-   `permission_id` -- UUID primary key
-   `name` -- unique
-   `description`

#### `user_roles`

Many-to-many relationship between accounts and global roles.

-   `user_account_id` -- foreign key to `user_accounts`
-   `role_id` -- foreign key to `roles`
-   Composite primary key: (`user_account_id`, `role_id`)

#### `role_permissions`

Many-to-many relationship between roles and permissions.

-   `role_id` -- foreign key to `roles`
-   `permission_id` -- foreign key to `permissions`
-   Composite primary key: (`role_id`, `permission_id`)

### 8.3 Organizations

#### `organizations`

Stores partner and affiliated institutions.

-   `organization_id` -- UUID primary key
-   `name`
-   `organization_type`
-   `description`
-   `website`
-   `address`
-   `verification_status`

#### `person_organizations`

Connects people to their institutions and records professional
affiliations.

-   `person_id` -- foreign key to `persons`
-   `organization_id` -- foreign key to `organizations`
-   `position`
-   `department`
-   `start_date`
-   `end_date`
-   `is_primary`
-   Composite primary key or a suitable unique key for the affiliation
    record

A partial unique index can enforce at most one current primary
affiliation per person if that is a business requirement.

### 8.4 Projects

#### `projects`

Stores initiative projects.

-   `project_id` -- UUID primary key
-   `title`
-   `slug` -- unique
-   `description`
-   `problem_statement`
-   `objectives`
-   `focus_area`
-   `project_lead_id` -- foreign key to `persons`
-   `status` -- `proposed`, `under_review`, `approved`, `active`,
    `completed`, `archived`, or `rejected`
-   `visibility` -- `public` or `members`
-   `start_date`
-   `end_date`

#### `project_members`

Connects approved members to projects.

-   `project_id` -- foreign key to `projects`
-   `person_id` -- foreign key to `persons`
-   `project_role`
-   `responsibilities`
-   `status` -- `invited`, `active`, `left`, or `removed`
-   `joined_at`
-   Composite primary key: (`project_id`, `person_id`)

Project roles should be scoped to a project. For example, being a
project lead should not automatically make someone a platform
administrator.

### 8.5 Datasets

#### `datasets`

Stores dataset records and governance metadata.

-   `dataset_id` -- UUID primary key
-   `title`
-   `description`
-   `domain`
-   `data_source`
-   `collection_method`
-   `format`
-   `license`
-   `access_level` -- `public`, `members`, or `restricted`
-   `approval_status` -- `pending`, `approved`, `rejected`, or
    `archived`
-   `project_id` -- nullable foreign key to `projects`
-   `submitted_by` -- foreign key to `persons`
-   `created_at`

#### `dataset_versions`

Stores versioned dataset files and validation information.

-   `dataset_version_id` -- UUID primary key
-   `dataset_id` -- foreign key to `datasets`
-   `version_number`
-   `storage_key`
-   `documentation_url`
-   `checksum`
-   `validation_status` -- `pending`, `validated`, or `rejected`
-   `created_at`
-   Unique constraint: (`dataset_id`, `version_number`)

#### `dataset_contributors`

Connects members to datasets and records their contributions.

-   `dataset_id` -- foreign key to `datasets`
-   `person_id` -- foreign key to `persons`
-   `contribution_role`
-   Composite primary key: (`dataset_id`, `person_id`)

Keep dataset approval status separate from access level. A dataset
should not become publicly accessible merely because it has been
submitted or technically validated.

### 8.6 Products

#### `products`

Stores digital health products and prototypes.

-   `product_id` -- UUID primary key
-   `name`
-   `description`
-   `category`
-   `problem_addressed`
-   `development_status` -- `idea`, `development`, `prototype`,
    `testing`, `deployed`, or `discontinued`
-   `project_id` -- nullable foreign key to `projects`
-   `demo_url`
-   `repository_url`
-   `approval_status` -- `pending`, `approved`, `rejected`, or
    `archived`
-   `created_at`

#### `product_contributors`

Connects members to products.

-   `product_id` -- foreign key to `products`
-   `person_id` -- foreign key to `persons`
-   `contribution_role`
-   Composite primary key: (`product_id`, `person_id`)

Product development status and publication approval are separate
concepts.

### 8.7 Research and publications

#### `publications`

Stores research outputs.

-   `publication_id` -- UUID primary key
-   `title`
-   `abstract`
-   `publication_type`
-   `doi`
-   `publication_url`
-   `publication_date`
-   `project_id` -- nullable foreign key to `projects`
-   `approval_status`

#### `publication_authors`

Connects people to publications and preserves author order.

-   `publication_id` -- foreign key to `publications`
-   `person_id` -- foreign key to `persons`
-   `author_order` -- positive integer
-   Composite primary key: (`publication_id`, `person_id`)
-   Unique constraint: (`publication_id`, `author_order`)

### 8.8 Communities and discussions

#### `communities`

Stores Communities of Practice and member working groups.

-   `community_id` -- UUID primary key
-   `name` -- unique
-   `description`
-   `focus_area`
-   `community_lead_id` -- foreign key to `persons`
-   `status` -- `active`, `inactive`, or `archived`

#### `community_members`

Connects members to communities.

-   `community_id` -- foreign key to `communities`
-   `person_id` -- foreign key to `persons`
-   `community_role`
-   `joined_at`
-   Composite primary key: (`community_id`, `person_id`)

#### `discussions`

Stores discussion topics within communities.

-   `discussion_id` -- UUID primary key
-   `community_id` -- foreign key to `communities`
-   `author_id` -- foreign key to `persons`
-   `title`
-   `content`
-   `created_at`

#### `comments`

Stores comments and threaded replies.

-   `comment_id` -- UUID primary key
-   `discussion_id` -- foreign key to `discussions`
-   `author_id` -- foreign key to `persons`
-   `parent_comment_id` -- nullable self-referencing foreign key to
    `comments`
-   `content`
-   `created_at`

### 8.9 Other platform modules

The following tables should be included as the design is completed:

-   `events`
-   `event_registrations`
-   `opportunities`
-   `applications`
-   `partnerships`
-   `notifications`
-   `audit_logs`
-   `membership_reviews`
-   `dataset_access_requests`

These support events, calls for participation, partnership records,
notifications, traceability, membership decision history, and controlled
dataset access.

## 9. Relationship overview

``` mermaid
erDiagram
    PERSON ||--o| USER_ACCOUNT : has
    PERSON ||--o| MEMBERSHIP : holds
    MEMBERSHIP_TYPE ||--o{ MEMBERSHIP : classifies
    USER_ACCOUNT ||--o{ USER_ROLE : assigned
    ROLE ||--o{ USER_ROLE : includes
    ROLE ||--o{ ROLE_PERMISSION : grants
    PERMISSION ||--o{ ROLE_PERMISSION : included_in

    PERSON ||--o{ PERSON_ORGANIZATION : affiliated
    ORGANIZATION ||--o{ PERSON_ORGANIZATION : includes

    PERSON ||--o{ PROJECT : leads
    PROJECT ||--o{ PROJECT_MEMBER : has
    PERSON ||--o{ PROJECT_MEMBER : joins

    PROJECT ||--o{ DATASET : relates_to
    DATASET ||--o{ DATASET_VERSION : has
    DATASET ||--o{ DATASET_CONTRIBUTOR : has
    PERSON ||--o{ DATASET_CONTRIBUTOR : contributes

    PROJECT ||--o{ PRODUCT : relates_to
    PRODUCT ||--o{ PRODUCT_CONTRIBUTOR : has
    PERSON ||--o{ PRODUCT_CONTRIBUTOR : contributes

    PROJECT ||--o{ PUBLICATION : produces
    PUBLICATION ||--o{ PUBLICATION_AUTHOR : has
    PERSON ||--o{ PUBLICATION_AUTHOR : authors

    PERSON ||--o{ COMMUNITY : leads
    COMMUNITY ||--o{ COMMUNITY_MEMBER : has
    PERSON ||--o{ COMMUNITY_MEMBER : joins
    COMMUNITY ||--o{ DISCUSSION : contains
    PERSON ||--o{ DISCUSSION : writes
    DISCUSSION ||--o{ COMMENT : receives
    PERSON ||--o{ COMMENT : writes
    COMMENT o|--o{ COMMENT : replies_to
```

## 10. Key constraints and integrity rules

1.  Each person may have at most one user account.
2.  Email addresses must be unique without regard to letter case.
3.  Each person has one current membership record in the simple
    current-state model.
4.  Internal collaboration requires an approved, unexpired membership
    and an active user account.
5.  Junction tables use composite primary keys to prevent duplicate
    relationships.
6.  Dataset version numbers must be unique within each dataset.
7.  Publication author order must be unique within each publication and
    greater than zero.
8.  Project start dates must not be later than project end dates.
9.  Affiliation end dates must not precede start dates.
10. Dataset approval, dataset validation, and dataset access level must
    remain distinct.
11. Product development status and product publication approval must
    remain distinct.
12. Use restrictive deletion rules for research and governance records
    where deleting a person or project would damage historical
    attribution.

## 11. Authorization and security

A database trigger can check membership when a member is added to a
project, dataset, product, or community. However, an insert-time trigger
alone is not sufficient: it does not automatically revoke existing
access when a membership expires or is suspended.

The application must recheck authorization on every protected API
request and read. Consider PostgreSQL Row-Level Security (RLS) for
additional database-level protection.

Recommended controls:

-   Hash passwords with Argon2id.
-   Use TLS for network traffic.
-   Encrypt sensitive data at rest.
-   Apply least-privilege permissions.
-   Record sensitive administrative actions in audit logs.
-   Use regular backups and test restoration.
-   Store uploaded files in object storage; keep metadata and storage
    keys in PostgreSQL.
-   Restrict sensitive health datasets and require appropriate legal
    authority, consent, de-identification, and access review.
-   Never publish identifiable patient information as an open dataset.

## 12. Important implementation decisions still to validate

Before treating the schema as production-ready, confirm:

-   Whether membership applications and decision history need a separate
    table.
-   Whether a person can hold multiple concurrent membership categories.
-   Whether organizations can formally lead, fund, or partner on
    projects through a dedicated project-organization junction table.
-   Whether dataset curators and reviewers need explicit assignment
    tables.
-   Whether project leads must also appear in `project_members`.
-   Whether one current primary organizational affiliation per person
    should be enforced.
-   Which events, opportunities, discussions, and notifications are
    public versus members-only.
-   Whether dataset access requires a formal request and approval
    workflow.

## 13. Recommended next steps

1.  Review and finalize the ERD and business rules.
2.  Complete the PostgreSQL DDL and migration sequence.
3.  Define FastAPI endpoints and authorization policies.
4.  Design the public website, member dashboard, and leadership/admin
    workspace.
5.  Implement authentication, membership review, and role-based access
    first.
6.  Add project, dataset, product, research, and community workflows.
7.  Test permissions, auditability, backups, and data governance before
    launch.

------------------------------------------------------------------------

**Status:** Architecture and schema foundation for collaborative review.
This document is a design baseline, not a complete production migration
or security audit.
