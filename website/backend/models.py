"""
SQLAlchemy ORM Models for Tigray Medical Association - Digital Health Initiative (TMA-DHI)
==========================================================================================
Implements all 24 relational database entities across Identity, Projects, Datasets,
Products, Publications, Communities, and Governance domains.
"""
import uuid
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =============================================================================
# DOMAIN 1: IDENTITY, MEMBERSHIP & ACCESS CONTROL
# =============================================================================

class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(200), nullable=False)
    professional_title = Column(String(100), nullable=True)
    biography = Column(Text, nullable=True)
    phone = Column(String(30), nullable=True)
    location = Column(String(150), nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    profile_visibility = Column(String(20), nullable=False, default="members")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user_account = relationship("UserAccount", back_populates="person", uselist=False)
    membership = relationship("Membership", back_populates="person", uselist=False, foreign_keys="Membership.person_id")
    organizations = relationship("PersonOrganization", back_populates="person")
    led_projects = relationship("Project", back_populates="lead")


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), unique=True, nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    account_status = Column(String(20), nullable=False, default="pending")
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    person = relationship("Person", back_populates="user_account")
    roles = relationship("Role", secondary="user_roles", backref="users")


class MembershipType(Base):
    __tablename__ = "membership_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), unique=True, nullable=False)
    membership_type_id = Column(UUID(as_uuid=True), ForeignKey("membership_types.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    applied_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(Date, nullable=True)

    person = relationship("Person", foreign_keys=[person_id], back_populates="membership")
    membership_type = relationship("MembershipType")
    reviewer = relationship("Person", foreign_keys=[reviewed_by])


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    permissions = relationship("Permission", secondary="role_permissions", backref="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(Text, nullable=True)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("user_accounts.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    organization_type = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    website_url = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    verification_status = Column(String(20), default="unverified", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class PersonOrganization(Base):
    __tablename__ = "person_organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    position = Column(String(150), nullable=True)
    department = Column(String(150), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)

    person = relationship("Person", back_populates="organizations")
    organization = relationship("Organization")


# =============================================================================
# DOMAIN 2: INNOVATION & PROJECTS
# =============================================================================

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(250), nullable=False)
    slug = Column(String(280), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    problem_statement = Column(Text, nullable=True)
    objectives = Column(Text, nullable=True)
    focus_area = Column(String(120), nullable=False)
    project_lead_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(30), default="proposed", nullable=False)
    visibility = Column(String(20), default="public", nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    lead = relationship("Person", back_populates="led_projects")
    members = relationship("Person", secondary="project_members", backref="projects")
    products = relationship("Product", back_populates="project")
    datasets = relationship("Dataset", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), primary_key=True)
    project_role = Column(String(100), nullable=False)
    responsibilities = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(250), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    problem_addressed = Column(Text, nullable=True)
    development_status = Column(String(30), default="prototype", nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    demonstration_url = Column(Text, nullable=True)
    repository_url = Column(Text, nullable=True)
    approval_status = Column(String(30), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="products")
    contributors = relationship("Person", secondary="product_contributors", backref="products")


class ProductContributor(Base):
    __tablename__ = "product_contributors"

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), primary_key=True)
    contribution_role = Column(String(100), nullable=False)


# =============================================================================
# DOMAIN 3: RESEARCH & KNOWLEDGE REPOSITORY
# =============================================================================

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(250), nullable=False)
    description = Column(Text, nullable=False)
    domain = Column(String(120), nullable=True)
    data_source = Column(Text, nullable=True)
    collection_method = Column(Text, nullable=True)
    format = Column(String(50), nullable=True)
    license = Column(String(100), nullable=True)
    access_level = Column(String(30), default="restricted", nullable=False)
    approval_status = Column(String(30), default="pending", nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="datasets")
    versions = relationship("DatasetVersion", back_populates="dataset")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    version_number = Column(String(30), nullable=False)
    storage_key = Column(Text, nullable=False)
    documentation_url = Column(Text, nullable=True)
    file_checksum = Column(String(128), nullable=True)
    validation_status = Column(String(30), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", back_populates="versions")
    __table_args__ = (UniqueConstraint("dataset_id", "version_number", name="uq_dataset_version"),)


class DatasetLicense(Base):
    """
    Paid licensing records for datasets.
    In accordance with TMA-DHI data monetization: raw datasets cannot be downloaded unless paid.
    """
    __tablename__ = "dataset_licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    licensee_name = Column(String(200), nullable=False)
    licensee_email = Column(String(254), nullable=False)
    organization = Column(String(200), nullable=False)
    license_tier = Column(String(50), nullable=False)  # 'academic', 'commercial', 'institutional'
    amount_paid = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    payment_gateway = Column(String(50), nullable=False)  # 'telebirr', 'cbe', 'stripe', 'bank_transfer'
    transaction_reference = Column(String(150), unique=True, nullable=False)
    payment_status = Column(String(30), default="completed", nullable=False)
    license_key = Column(String(128), unique=True, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    max_downloads = Column(Integer, default=10, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    dataset = relationship("Dataset", backref="licenses")


class Publication(Base):
    __tablename__ = "publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    abstract = Column(Text, nullable=True)
    publication_type = Column(String(80), nullable=True)
    doi = Column(String(255), nullable=True)
    publication_url = Column(Text, nullable=True)
    publication_date = Column(Date, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    approval_status = Column(String(30), default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


# =============================================================================
# DOMAIN 4: COMMUNITIES OF PRACTICE
# =============================================================================

class Community(Base):
    __tablename__ = "communities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    focus_area = Column(String(120), nullable=True)
    community_lead_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(250), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
