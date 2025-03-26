# pylint: skip-file

from sqlalchemy import Column, ForeignKey, Text, Boolean, Integer, ForeignKeyConstraint, Index, \
    DateTime, MetaData, and_, UniqueConstraint
from sqlalchemy import String
from sqlalchemy import Enum
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import relationship, declarative_base, InstrumentedAttribute
from sqlalchemy import inspect
from sqlalchemy.schema import DropTable
from sqlalchemy.dialects.postgresql import DropEnumType, JSONB
from sqlalchemy.ext.compiler import compiles

from middleware.common.metadatabase.model.types.component_templates_acl_relation_types_enum import \
    ComponentTemplatesACLRelationTypesEnum
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum
from middleware.common.metadatabase.model.types.object_types_enum import ObjectTypesEnum
from middleware.common.metadatabase.model.types.objects_acl_relation_types_enum import ObjectsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.permission_actions_effects_enum import PermissionEffectsEnum
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.metadatabase.model.types.secrets_acl_relation_types_enum import SecretsACLRelationTypesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum

from middleware.common.metadatabase.model.types.permissions_acl_relation_types_enum import \
    PermissionsACLRelationTypesEnum

"""
BASE DECLARATION
"""

Base = declarative_base()


class BaseTableModel(Base):
    __abstract__ = True

    def insert(self, session, commit=True):
        """
        Insert object into MetaDB
        """
        session.add(self)
        if commit:
            session.commit()
        return self

    def update(self, session, commit=True):
        """
        Update instance of object

        return: updated object
        """
        # merge currently existing object with all object with the same ID in whole session first
        # as a result should be updated object or the self instance registered in session
        obj_to_update = session.merge(self)
        # if object is mark as modified
        if inspect(obj_to_update).modified:
            # nothing is needed, only commit already updated base model objects which are registered in session
            if commit:
                session.commit()
        return obj_to_update

    def delete(self, session, commit=True):
        """
        Delete instance of object

        return: deleted object
        """
        # merge currently existing object with all object with the same ID in whole session first
        # as a result should be registered object with no conflicts
        obj_to_delete = session.merge(self)
        session.delete(obj_to_delete)
        if commit:
            session.commit()
        return obj_to_delete

    def get_unique(self, session, merge=False):
        """
        Get DB result from DB based on primary keys in BaseTableModel instance

        :param session
        :param merge - if true, then merge the self with new retrieved object

        :return - BaseTableModel instance of record or None
        """
        primary_keys = []
        for attr_name in dir(self.__class__):
            attr_definition = getattr(self.__class__, attr_name)
            if type(attr_definition) == InstrumentedAttribute and \
                    hasattr(attr_definition, "primary_key") and attr_definition.primary_key:
                primary_keys.append(attr_definition)
        db_unique_record = session.query(self.__class__).filter(
            *[pk_definition == getattr(self, pk_definition.name) for pk_definition in primary_keys]).one_or_none()
        if db_unique_record is not None and merge:
            # it will take self instance and merge it with newly retrieved instance based on IDs
            db_unique_record = session.merge(self)
        return db_unique_record

    @compiles(DropTable, "postgresql")
    def _compile_drop_table(element, compiler, **kwargs):
        """
        Need to provide CASCADE for the removal of the table
        """
        return compiler.visit_drop_table(element) + " CASCADE"

    @compiles(DropEnumType, "postgresql")
    def _compile_drop_type(element, compiler, **kwargs):
        """
        Need to provide CASCADE for the removal of the enum type
        """
        return compiler.visit_drop_enum_type(element) + " CASCADE"

    @staticmethod
    def drop_table(table_name, engine):
        """
        The custom drop table method
        :param table_name: The name of the table to remove
        :param engine: The sqlalchemy engine
        """
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = metadata.tables.get(table_name)
        if table is not None:
            Base.metadata.drop_all(engine, [table], checkfirst=True)

    @staticmethod
    def drop_tables_if_not_exists(bind):
        """
        Drop all tables from model if the table exists in target DB

        :param bind - connection or engine represent link to target DB
        """
        # need to reverse order of sorted list because of dependencies issues
        for table_to_drop in Base.metadata.sorted_tables[::-1]:
            try:
                BaseTableModel.drop_table(table_to_drop.name, bind)
            except ProgrammingError as db_ex:
                if not "Unknown table" in str(db_ex):
                    raise

    @classmethod
    def get_many(cls, session, filter_condition=None, ordering_columns_list: list = None):
        """
        Get all objects of this method

        :param filter_condition: - lambda of filter condition. Input should be whatever SQL alchemy expression.
        :param session:
        :param ordering_columns_list:
        """

        query_exp = session.query(cls)
        if filter_condition is not None:
            query_exp = query_exp.filter(filter_condition)
        if ordering_columns_list is not None:
            query_exp = query_exp.order_by(*ordering_columns_list)
        return query_exp.all()

    @classmethod
    def delete_many(cls, session, filter_condition=None, commit=True):
        """
        Get all objects of this method

        :param filter_condition - lambda of filter condition. Input should be whatever SQL alchemy expression.
        :param session
        :param commit
        """
        query_exp = session.query(cls)
        if filter_condition is not None:
            query_exp = query_exp.filter(filter_condition)
        query_exp.delete()
        if commit:
            session.commit()

    def get_pk_values(self):
        """
        method return dict of {ColumnName: ColumnValue} of PKs
        """
        pass


"""
======================================== SUBJECTS RELATED TABLES ======================================== 
"""


class Subjects(BaseTableModel):
    """
    Class represent SUBJECTS table
    """
    __tablename__ = 'SUBJECTS'

    SUBJECT_ID = Column(String(255), primary_key=True)
    SUBJECT_TYPE = Column(Enum(SubjectTypesEnum))
    DISPLAY_NAME = Column(String(255))
    DESCRIPTION = Column(String(512))
    IS_ENABLED = Column(Boolean)
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)

    # Relation objects raise_on_sql
    rel_permissions_acl = relationship("PermissionsACL", foreign_keys='PermissionsACL.SUBJECT_ID',
                                       back_populates="rel_subject", lazy='dynamic', cascade="all, delete")
    rel_permissions_acl_master = relationship("PermissionsACL", foreign_keys='PermissionsACL.MASTER_OWNER',
                                              back_populates="rel_subject_master", lazy='dynamic')
    rel_secrets_acl = relationship("SecretsACL", back_populates='rel_subject', lazy='raise_on_sql',
                                   cascade="all, delete")

    rel_project_account_settings = relationship('ProjectAccountSettings', back_populates='rel_project',
                                                lazy='raise_on_sql')
    rel_project_properties = relationship('ProjectProperties', back_populates='rel_project', lazy='raise_on_sql',
                                          cascade="all, delete")
    rel_notifications = relationship('Notifications', back_populates='rel_project', lazy='raise_on_sql',
                                     cascade="all, delete")
    rel_objects_acl = relationship('ObjectsACL', back_populates='rel_subject', lazy='raise_on_sql',
                                   cascade="all, delete")
    rel_component_templates_acl = relationship('ComponentsTemplatesACL', back_populates='rel_subject',
                                               lazy='raise_on_sql', cascade="all, delete")

    # Relation objects
    rel_parent_subjects = relationship("Subjects", secondary="SUBJECTS_HIERARCHY",
                                       back_populates='rel_children_subjects',
                                       foreign_keys="SubjectsHierarchy.PARENT_ID", lazy='dynamic',
                                       cascade="all, delete")
    rel_children_subjects = relationship("Subjects", secondary="SUBJECTS_HIERARCHY",
                                         back_populates='rel_parent_subjects',
                                         foreign_keys="SubjectsHierarchy.CHILD_ID", lazy='dynamic',
                                         cascade="all, delete")

    def get_pk_values(self):
        return {
            Subjects.SUBJECT_ID.name: self.SUBJECT_ID
        }


class SubjectsHierarchy(BaseTableModel):
    """
    Class represent SUBJECTS_HIERARCHY table
    """
    __tablename__ = 'SUBJECTS_HIERARCHY'

    CHILD_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID, ondelete='CASCADE'), primary_key=True)
    PARENT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID, ondelete='CASCADE'), primary_key=True)

    def get_pk_values(self):
        return {
            SubjectsHierarchy.CHILD_ID.name: self.CHILD_ID,
            SubjectsHierarchy.PARENT_ID.name: self.PARENT_ID,
        }


"""
======================================== SECRETS RELATED TABLES ======================================== 
"""


class Secrets(BaseTableModel):
    """
    Table represent SECRETS table
    """
    __tablename__ = 'SECRETS'

    SECRET_NAME = Column(String(255), nullable=False, primary_key=True)
    SECRET_MANAGER_NAME = Column(String(255), nullable=False)
    DESCRIPTION = Column(String(512))
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)

    # Relation objects
    rel_secrets_acl = relationship('SecretsACL', cascade='all, delete', back_populates='rel_secret', lazy='joined')

    def get_pk_values(self):
        return {
            Secrets.SECRET_NAME.name: self.SECRET_NAME
        }


class SecretsACL(BaseTableModel):
    """
    Class represent SECRETS_ACL table
    """
    __tablename__ = 'SECRETS_ACL'

    SECRET_NAME = Column(String(255), ForeignKey(Secrets.SECRET_NAME), primary_key=True)
    SUBJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)
    RELATION_TYPE = Column(Enum(SecretsACLRelationTypesEnum), primary_key=True)

    # Relation objects
    # do not need to load this relation, therefore lazy='raise_on_sql'
    rel_subject = relationship('Subjects', back_populates='rel_secrets_acl', lazy='joined', innerjoin=True,
                               uselist=False)
    rel_secret = relationship('Secrets', back_populates='rel_secrets_acl', lazy='joined', innerjoin=True, uselist=False)

    def get_pk_values(self):
        return {
            SecretsACL.SECRET_NAME.name: self.SECRET_NAME,
            SecretsACL.SUBJECT_ID.name: self.SUBJECT_ID,
            SecretsACL.RELATION_TYPE.name: self.RELATION_TYPE
        }


"""
======================================== OBJECT/COMPONENTS RELATED TABLES ======================================== 
"""


class DifwCoreVersions(BaseTableModel):
    """
    Table represent DIFW_CORE_VERSIONS table
    """
    __tablename__ = 'DIFW_CORE_VERSIONS'

    DIFW_CORE_VERSION = Column(String(255), nullable=False, primary_key=True)
    IS_ENABLED = Column(Boolean)
    IS_LATEST = Column(Boolean)

    # Relation objects
    # prevent loading of this attr by relationship raise_on_sql. It is not needed to load it here
    rel_component_types = relationship('ComponentTypes', back_populates="rel_core_version", lazy='raise_on_sql')
    rel_objects = relationship('Objects', back_populates="rel_core_version", lazy='raise_on_sql')

    def get_pk_values(self):
        return {
            DifwCoreVersions.DIFW_CORE_VERSION.name: self.DIFW_CORE_VERSION
        }


class ComponentTypes(BaseTableModel):
    """
    Class represent COMPONENT_TYPES table
    """
    __tablename__ = 'COMPONENT_TYPES'

    # Columns
    COMPONENT_TYPE_NAME = Column(String(255), primary_key=True)
    COMPONENT_TYPE_CATEGORY = Column(Enum(ComponentTypeCategoriesEnum), primary_key=True)
    DEFINITION = Column(Text)
    DIFW_CORE_VERSION = Column(String(255), ForeignKey(DifwCoreVersions.DIFW_CORE_VERSION), primary_key=True)

    # Relation objects
    rel_core_version = relationship("DifwCoreVersions", back_populates="rel_component_types", lazy='joined')
    rel_components = relationship('Components', back_populates='rel_component_type', lazy='raise_on_sql')

    def get_pk_values(self):
        return {
            ComponentTypes.COMPONENT_TYPE_NAME.name: self.COMPONENT_TYPE_NAME,
            ComponentTypes.COMPONENT_TYPE_CATEGORY.name: self.COMPONENT_TYPE_CATEGORY
        }


class Components(BaseTableModel):
    """
    Class represent COMPONENTS table
    """
    __tablename__ = 'COMPONENTS'

    COMPONENT_ID = Column(Integer, primary_key=True, nullable=False, name="COMPONENT_ID", autoincrement=True)
    COMPONENT_NAME = Column(String(255), nullable=False, name="COMPONENT_NAME")
    DEFINITION = Column(Text)
    DESCRIPTION = Column(Text)
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)
    PROPERTIES = Column(JSONB)

    COMPONENT_TYPE_NAME = Column(String(255), name="COMPONENT_TYPE_NAME")
    COMPONENT_TYPE_CATEGORY = Column(Enum(ComponentTypeCategoriesEnum), name="COMPONENT_TYPE_CATEGORY")
    DIFW_CORE_VERSION = Column(String(255), name="DIFW_CORE_VERSION")

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                COMPONENT_TYPE_NAME.name,
                COMPONENT_TYPE_CATEGORY.name,
                DIFW_CORE_VERSION.name
            ],
            [
                f'{ComponentTypes.__tablename__}.{ComponentTypes.COMPONENT_TYPE_NAME.name}',
                f'{ComponentTypes.__tablename__}.{ComponentTypes.COMPONENT_TYPE_CATEGORY.name}',
                f'{ComponentTypes.__tablename__}.{ComponentTypes.DIFW_CORE_VERSION.name}'
            ]
        ),
        Index('idx_components_id_and_name', COMPONENT_ID.name, COMPONENT_NAME.name)
    )

    # Relation objects
    rel_component_type = relationship("ComponentTypes", back_populates="rel_components", lazy='joined', uselist=False)
    rel_component_template = relationship("ComponentTemplates", back_populates="rel_component", lazy='raise_on_sql',
                                          cascade="all, delete")
    rel_object_components = relationship("ObjectComponents", back_populates="rel_component", lazy='raise_on_sql',
                                         cascade="all, delete")

    def get_pk_values(self):
        return {
            Components.COMPONENT_ID.name: self.COMPONENT_ID
        }


class ComponentTemplates(BaseTableModel):
    """
    Class represent COMPONENT_TEMPLATES table
    """
    __tablename__ = 'COMPONENT_TEMPLATES'

    TEMPLATE_ID = Column(Integer, primary_key=True, nullable=False, name="TEMPLATE_ID")
    TEMPLATE_NAME = Column(String(255), nullable=False, name="TEMPLATE_NAME", unique=True)
    IS_LATEST = Column(Boolean)

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                TEMPLATE_ID.name
            ],
            [
                f'{Components.__tablename__}.{Components.COMPONENT_ID.name}'
            ]
        ),
        Index('idx_components_templates_id_and_name', TEMPLATE_ID.name, TEMPLATE_NAME.name)
    )

    # Relation objects
    rel_component = relationship("Components", back_populates="rel_component_template", lazy='joined', uselist=False,
                                 cascade="all, delete")
    rel_component_templates_acl = relationship("ComponentsTemplatesACL", back_populates="rel_template", lazy='select',
                                               cascade="all, delete")

    def get_pk_values(self):
        return {
            ComponentTemplates.TEMPLATE_ID.name: self.TEMPLATE_ID
        }


class ComponentsTemplatesACL(BaseTableModel):
    """
    Class represent COMPONENTS_TEMPLATES_ACL table
    """
    __tablename__ = 'COMPONENTS_TEMPLATES_ACL'

    TEMPLATE_ID = Column(Integer, primary_key=True, name="TEMPLATE_ID")
    TEMPLATE_NAME = Column(String(255), primary_key=True, name="TEMPLATE_NAME")
    SUBJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)
    RELATION_TYPE = Column(Enum(ComponentTemplatesACLRelationTypesEnum), primary_key=True)
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                TEMPLATE_ID.name
            ],
            [
                f'{ComponentTemplates.__tablename__}.{ComponentTemplates.TEMPLATE_ID.name}'
            ]
        ),
    )

    # Relation objects
    # do not need to load this relation, therefore lazy='raise_on_sql'
    rel_subject = relationship('Subjects', back_populates='rel_component_templates_acl', lazy='joined', uselist=False)
    rel_template = relationship('ComponentTemplates', back_populates='rel_component_templates_acl', lazy='select',
                                uselist=False)

    def get_pk_values(self):
        return {
            ComponentsTemplatesACL.TEMPLATE_ID.name: self.TEMPLATE_ID,
            ComponentsTemplatesACL.SUBJECT_ID.name: self.SUBJECT_ID,
            ComponentsTemplatesACL.RELATION_TYPE.name: self.RELATION_TYPE
        }


class Objects(BaseTableModel):
    """
    Class represent OBJECTS table
    """
    __tablename__ = 'OBJECTS'

    OBJECT_FULL_NAME = Column(String(255), primary_key=True, nullable=False, name="OBJECT_FULL_NAME")
    OBJECT_VERSION = Column(String(45), primary_key=True, nullable=False, name="OBJECT_VERSION")
    OBJECT_NAME = Column(String(100), nullable=False)
    OBJECT_TYPE = Column(Enum(ObjectTypesEnum))
    DISPLAY_NAME = Column(String(255))
    DESCRIPTION = Column(String(512))
    IS_DRAFT = Column(Boolean, nullable=False, default=False)
    IS_LATEST = Column(Boolean, nullable=False, default=True)
    IS_ENABLED = Column(Boolean, nullable=False, default=False)

    PARENT_OBJECT_FULL_NAME = Column(String(255), name="PARENT_OBJECT_FULL_NAME")
    PARENT_OBJECT_VERSION = Column(String(45), name="PARENT_OBJECT_VERSION")
    DIFW_CORE_VERSION = Column(String(255), ForeignKey(DifwCoreVersions.DIFW_CORE_VERSION))

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                PARENT_OBJECT_FULL_NAME.name,
                PARENT_OBJECT_VERSION.name
            ],
            [
                f'{__tablename__}.{OBJECT_FULL_NAME.name}',
                f'{__tablename__}.{OBJECT_VERSION.name}'
            ]
        ),
    )

    # Relation objects
    rel_parent_object = relationship("Objects", remote_side=[OBJECT_FULL_NAME, OBJECT_VERSION], lazy='select',
                                     uselist=False, cascade="all, delete")
    rel_children_objects = relationship("Objects", lazy='dynamic', back_populates='rel_parent_object',
                                        cascade="save-update, merge, delete")
    rel_core_version = relationship("DifwCoreVersions", back_populates="rel_objects", lazy='select', uselist=False)
    rel_object_properties = relationship('ObjectProperties', back_populates='rel_object', lazy='joined',
                                         cascade="save-update, merge, delete, delete-orphan")
    rel_objects_acl = relationship('ObjectsACL', back_populates='rel_object', lazy='joined',
                                   cascade="all, delete-orphan")
    rel_object_components = relationship('ObjectComponents', back_populates='rel_object', lazy='select',
                                         cascade="save-update, merge, delete, delete-orphan")

    def get_pk_values(self):
        return {
            Objects.OBJECT_FULL_NAME.name: self.OBJECT_FULL_NAME,
            Objects.OBJECT_VERSION.name: self.OBJECT_VERSION
        }


class ObjectProperties(BaseTableModel):
    """
    Class represent OBJECT_PROPERTIES table
    """
    __tablename__ = 'OBJECT_PROPERTIES'

    OBJECT_FULL_NAME = Column(String(255), name="OBJECT_FULL_NAME", primary_key=True)
    OBJECT_VERSION = Column(String(45), name="OBJECT_VERSION", primary_key=True)
    PROPERTY_NAME = Column(String(255), primary_key=True)
    PROPERTY_BIGINT_VALUE = Column(DateTime)
    PROPERTY_STRING_VALUE = Column(String(255))
    PROPERTY_BOOL_VALUE = Column(Boolean)
    PROPERTY_LONGTEXT_VALUE = Column(Text)
    PROPERTY_INT_VALUE = Column(Integer)

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                OBJECT_FULL_NAME.name,
                OBJECT_VERSION.name
            ],
            [
                f'{Objects.__tablename__}.{Objects.OBJECT_FULL_NAME.name}',
                f'{Objects.__tablename__}.{Objects.OBJECT_VERSION.name}'
            ],
            ondelete="CASCADE"
        ),
    )
    # Relation objects
    rel_object = relationship('Objects', back_populates='rel_object_properties', lazy='select', uselist=True)

    def get_pk_values(self):
        return {
            ObjectProperties.OBJECT_FULL_NAME.name: self.OBJECT_FULL_NAME,
            ObjectProperties.OBJECT_VERSION.name: self.OBJECT_VERSION,
            ObjectProperties.PROPERTY_NAME.name: self.PROPERTY_NAME
        }


class ObjectsACL(BaseTableModel):
    """
    Class represent OBJECTS_ACL table
    """
    __tablename__ = 'OBJECTS_ACL'

    OBJECT_FULL_NAME = Column(String(255), name="OBJECT_FULL_NAME", primary_key=True)
    OBJECT_VERSION = Column(String(45), name="OBJECT_VERSION", primary_key=True)
    SUBJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)
    RELATION_TYPE = Column(Enum(ObjectsACLRelationTypesEnum), primary_key=True)
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)

    __table_args__ = (
        ForeignKeyConstraint(
            [
                OBJECT_FULL_NAME.name,
                OBJECT_VERSION.name
            ],
            [
                f'{Objects.__tablename__}.{Objects.OBJECT_FULL_NAME.name}',
                f'{Objects.__tablename__}.{Objects.OBJECT_VERSION.name}'
            ]
        ),
    )

    # Relation objects
    # do not need to load this relation, therefore lazy='raise_on_sql'
    rel_subject = relationship('Subjects', back_populates='rel_objects_acl', lazy='joined')
    rel_object = relationship('Objects', back_populates='rel_objects_acl', lazy='noload')

    def get_pk_values(self):
        return {
            ObjectsACL.OBJECT_FULL_NAME.name: self.OBJECT_FULL_NAME,
            ObjectsACL.OBJECT_VERSION.name: self.OBJECT_VERSION,
            ObjectsACL.SUBJECT_ID.name: self.SUBJECT_ID,
            ObjectsACL.RELATION_TYPE.name: self.RELATION_TYPE
        }


class ObjectComponentsHierarchy(BaseTableModel):
    """
    Class represent SUBJECTS_HIERARCHY table
    """
    __tablename__ = 'OBJECT_COMPONENTS_HIERARCHY'

    CHILD_COMPONENT_ID = Column(Integer, primary_key=True, name="CHILD_COMPONENT_ID")
    CHILD_OBJECT_FULL_NAME = Column(String(255), primary_key=True, name="CHILD_OBJECT_FULL_NAME")
    CHILD_OBJECT_VERSION = Column(String(45), primary_key=True, name="CHILD_OBJECT_VERSION")
    PARENT_COMPONENT_ID = Column(Integer, primary_key=True, name="PARENT_COMPONENT_ID")
    PARENT_OBJECT_FULL_NAME = Column(String(255), primary_key=True, name="PARENT_OBJECT_FULL_NAME")
    PARENT_OBJECT_VERSION = Column(String(45), primary_key=True, name="PARENT_OBJECT_VERSION")
    PROPERTIES = Column(JSONB)

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                CHILD_COMPONENT_ID.name,
                CHILD_OBJECT_FULL_NAME.name,
                CHILD_OBJECT_VERSION.name
            ],
            [
                'OBJECTS_COMPONENTS.COMPONENT_ID',
                'OBJECTS_COMPONENTS.OBJECT_FULL_NAME',
                'OBJECTS_COMPONENTS.OBJECT_VERSION'
            ]
            , ondelete="CASCADE"),
        ForeignKeyConstraint(
            [
                PARENT_COMPONENT_ID.name,
                PARENT_OBJECT_FULL_NAME.name,
                PARENT_OBJECT_VERSION.name
            ],
            [
                'OBJECTS_COMPONENTS.COMPONENT_ID',
                'OBJECTS_COMPONENTS.OBJECT_FULL_NAME',
                'OBJECTS_COMPONENTS.OBJECT_VERSION'
            ]
            , ondelete="CASCADE"),
    )

    # temporary reference for purpose of future development. it is not process by SQL alchemy
    intern_child_object_component_reference = None
    intern_parent_object_component_reference = None

    def get_pk_values(self):
        return {
            ObjectComponentsHierarchy.CHILD_COMPONENT_ID.name: self.OBJECT_FULL_NAME,
            ObjectComponentsHierarchy.CHILD_OBJECT_FULL_NAME.name: self.CHILD_OBJECT_FULL_NAME,
            ObjectComponentsHierarchy.CHILD_OBJECT_VERSION.name: self.CHILD_OBJECT_VERSION,
            ObjectComponentsHierarchy.PARENT_COMPONENT_ID.name: self.PARENT_COMPONENT_ID,
            ObjectComponentsHierarchy.PARENT_OBJECT_FULL_NAME.name: self.PARENT_OBJECT_FULL_NAME,
            ObjectComponentsHierarchy.PARENT_OBJECT_VERSION.name: self.PARENT_OBJECT_VERSION
        }


class ObjectComponents(BaseTableModel):
    """
    Class represent OBJECTS_COMPONENTS table
    """
    __tablename__ = 'OBJECTS_COMPONENTS'

    COMPONENT_ID = Column(Integer, primary_key=True, nullable=False, name="COMPONENT_ID", autoincrement=True)
    OBJECT_FULL_NAME = Column(String(255), name="OBJECT_FULL_NAME", primary_key=True)
    OBJECT_VERSION = Column(String(45), name="OBJECT_VERSION", primary_key=True)
    COMPONENT_NAME = Column(String(255), nullable=False, name="COMPONENT_NAME")
    OVERWRITE_COMPONENT_DEFINITION = Column(Text)
    COMPONENT_COORDINATES = Column(Text)

    # defining composite FK
    __table_args__ = (
        ForeignKeyConstraint(
            [
                COMPONENT_ID.name
            ],
            [
                f'{Components.__tablename__}.{Components.COMPONENT_ID.name}'
            ]
        ),
        ForeignKeyConstraint(
            [
                OBJECT_FULL_NAME.name,
                OBJECT_VERSION.name
            ],
            [
                f'{Objects.__tablename__}.{Objects.OBJECT_FULL_NAME.name}',
                f'{Objects.__tablename__}.{Objects.OBJECT_VERSION.name}'
            ],
            ondelete="CASCADE"
        ),
        UniqueConstraint(OBJECT_FULL_NAME.name, COMPONENT_NAME.name, name="unique_object_component_name")
    )

    # Relation objects
    rel_component = relationship("Components", back_populates="rel_object_components", lazy='joined',
                                 cascade="all, delete", uselist=False)
    rel_object = relationship('Objects', back_populates='rel_object_components', lazy='joined', cascade="all, delete")

    # if entity is going to relation as a child, then list of relations are the parents
    # the same is valid in different direction
    rel_parent_components_hierarchy = relationship(
        'ObjectComponentsHierarchy',
        cascade="save-update, merge, delete, delete-orphan",
        primaryjoin=and_(
            COMPONENT_ID == ObjectComponentsHierarchy.CHILD_COMPONENT_ID,
            OBJECT_FULL_NAME == ObjectComponentsHierarchy.CHILD_OBJECT_FULL_NAME,
            OBJECT_VERSION == ObjectComponentsHierarchy.CHILD_OBJECT_VERSION))

    rel_child_components_hierarchy = relationship(
        'ObjectComponentsHierarchy',
        cascade="save-update, merge, delete, delete-orphan",
        primaryjoin=and_(
            COMPONENT_ID == ObjectComponentsHierarchy.PARENT_COMPONENT_ID,
            OBJECT_FULL_NAME == ObjectComponentsHierarchy.PARENT_OBJECT_FULL_NAME,
            OBJECT_VERSION == ObjectComponentsHierarchy.PARENT_OBJECT_VERSION))

    def get_pk_values(self):
        return {
            ObjectComponents.COMPONENT_ID.name: self.COMPONENT_ID,
            ObjectComponents.OBJECT_FULL_NAME.name: self.OBJECT_FULL_NAME,
            ObjectComponents.OBJECT_VERSION.name: self.OBJECT_VERSION
        }


"""
======================================== PERMISSIONS RELATED TABLES ======================================== 
"""


class PermissionActionTypes(BaseTableModel):
    """
    Class represent PERMISSION_ACTION_TYPES table
    """
    __tablename__ = 'PERMISSION_ACTION_TYPES'

    ACTION_TYPE = Column(String(255), primary_key=True)
    DEFINITION = Column(Text)
    DESCRIPTION = Column(String(512))

    # Relation objects
    # do not need to load this relation, therefore lazy='raise_on_sql'
    rel_permission_actions = relationship("PermissionActions", back_populates="rel_permission_action_type",
                                          lazy='raise_on_sql')

    def get_pk_values(self):
        return {
            PermissionActionTypes.ACTION_TYPE.name: self.ACTION_TYPE
        }


class Permissions(BaseTableModel):
    """
    Class represent PERMISSIONS table
    """
    __tablename__ = 'PERMISSIONS'

    PERMISSION_NAME = Column(String(255), primary_key=True)
    EFFECT = Column(Enum(PermissionEffectsEnum))
    DESCRIPTION = Column(String(512))
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)
    IS_ENABLED = Column(Boolean)

    # Relation objects
    rel_permission_actions = relationship("PermissionActions", back_populates="rel_permissions", lazy='joined',
                                          cascade="save-update, merge,  delete", innerjoin=True)
    # removed lazy=dynamic since it is not possible to use contains_eager with it
    # maybe create a second another relationship with dynamic if needed
    rel_permissions_acl = relationship("PermissionsACL", back_populates="rel_permission", lazy='dynamic',
                                       cascade="all, delete", innerjoin=True)

    def get_pk_values(self):
        return {
            Permissions.PERMISSION_NAME.name: self.PERMISSION_NAME
        }


class PermissionActions(BaseTableModel):
    """
    Class represent PERMISSIONS table
    """
    __tablename__ = 'PERMISSION_ACTIONS'

    ACTION_ID = Column(Integer, primary_key=True, autoincrement=True)
    PERMISSION_NAME = Column(String(255), ForeignKey(Permissions.PERMISSION_NAME, ondelete='CASCADE',
                                                     onupdate='CASCADE'))
    ACTION_TYPE = Column(String(255), ForeignKey(PermissionActionTypes.ACTION_TYPE, ondelete='CASCADE'))
    ACTION_DETAIL = Column(Text)

    # Relation objects
    rel_permission_action_type = relationship('PermissionActionTypes', back_populates='rel_permission_actions',
                                              lazy='joined', uselist=False, innerjoin=True)
    # do not need to load this relation, therefore lazy='raise_on_sql'
    rel_permissions = relationship('Permissions', back_populates='rel_permission_actions', lazy='raise_on_sql')

    def get_pk_values(self):
        return {
            PermissionActions.ACTION_ID.name: self.ACTION_ID
        }


class PermissionsACL(BaseTableModel):
    """
    Class represent PERMISSIONS table
    """
    __tablename__ = 'PERMISSIONS_ACL'
    PERMISSION_NAME = Column(String(255), ForeignKey(Permissions.PERMISSION_NAME), primary_key=True)
    SUBJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)
    RELATION_TYPE = Column(Enum(PermissionsACLRelationTypesEnum), primary_key=True)
    MASTER_OWNER = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)

    # Relation objects
    # do not need to load this relation, therefore lazy='raise_on_sql'
    rel_permission = relationship('Permissions', back_populates='rel_permissions_acl', lazy='raise_on_sql',
                                  innerjoin=True)
    rel_subject = relationship('Subjects', back_populates='rel_permissions_acl', foreign_keys=[SUBJECT_ID],
                               lazy='joined', innerjoin=True, uselist=False)
    rel_subject_master = relationship('Subjects', back_populates='rel_permissions_acl_master',
                                      foreign_keys=[MASTER_OWNER], lazy='joined', innerjoin=True, uselist=False)

    def get_pk_values(self):
        return {
            PermissionsACL.PERMISSION_NAME.name: self.PERMISSION_NAME,
            PermissionsACL.SUBJECT_ID.name: self.SUBJECT_ID,
            PermissionsACL.RELATION_TYPE.name: self.RELATION_TYPE,
            PermissionsACL.MASTER_OWNER.name: self.MASTER_OWNER
        }


"""
======================================== PROJECT ACCOUNTS RELATED TABLES ======================================== 
"""


class ProjectAccountSettings(BaseTableModel):
    """
    Class represent PROJECT_ACCOUNT_SETTINGS table
    """
    __tablename__ = 'PROJECT_ACCOUNT_SETTINGS'

    PROJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)
    ACCOUNT_TYPE = Column(Enum(ProjectAccountTypesEnum), primary_key=True)
    ACCOUNT_DETAILS = Column(Text)
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)

    # Relation objects
    rel_project = relationship('Subjects', back_populates='rel_project_account_settings', lazy='select')

    def get_pk_values(self):
        return {
            ProjectAccountSettings.PROJECT_ID.name: self.PROJECT_ID,
            ProjectAccountSettings.ACCOUNT_TYPE.name: self.ACCOUNT_TYPE
        }


class ProjectProperties(BaseTableModel):
    """
    Class represent PROJECT_PROPERTIES table
    """
    __tablename__ = 'PROJECT_PROPERTIES'

    PROJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID), primary_key=True)
    PROPERTIES = Column(JSONB)
    LAST_MODIFIED_ID = Column(String(255))
    LAST_MODIFIED_TIME = Column(DateTime)

    # Relation objects
    rel_project = relationship('Subjects', back_populates='rel_project_properties', lazy='select', uselist=False)

    def get_pk_values(self):
        return {
            ProjectProperties.PROJECT_ID.name: self.PROJECT_ID
        }


class Notifications(BaseTableModel):
    """
    Class represent NOTIFICATIONS table
    """
    __tablename__ = 'NOTIFICATIONS'

    NOTIFICATION_ID = Column(Integer, primary_key=True, nullable=False, name="NOTIFICATION_ID", autoincrement=True)
    NOTIFICATION_NAME = Column(String(255))
    PROJECT_ID = Column(String(255), ForeignKey(Subjects.SUBJECT_ID))
    TEXT = Column(Text)
    TITLE = Column(String(255))
    HEX_RGB_COLOR = Column(String(16))
    VALID_FROM = Column(DateTime)
    VALID_TO = Column(DateTime)
    IS_ENABLED = Column(Boolean)
    CREATOR_ID = Column(String(255))
    LAST_MODIFIED_ID = Column(String(255))
    CREATED_TIME = Column(DateTime)
    LAST_MODIFIED_TIME = Column(DateTime)

    # Relation objects
    rel_project = relationship('Subjects', back_populates='rel_notifications', lazy='select', uselist=False)

    def get_pk_values(self):
        return {
            Notifications.NOTIFICATION_NAME.name: self.NOTIFICATION_NAME
        }


"""
======================================== Enumerators TABLE ======================================== 
"""


class Enumerators(BaseTableModel):
    """
    Class represent ENUMERATORS table
    """
    __tablename__ = 'ENUMERATORS'

    ENUMERATOR_CATEGORY = Column(String(255), primary_key=True)
    ENUMERATOR_VALUE = Column(String(255), primary_key=True)
    DISPLAY_NAME = Column(String(255), nullable=False)

    def get_pk_values(self):
        return {
            Enumerators.ENUMERATOR_CATEGORY.name: self.ENUMERATOR_CATEGORY,
            Enumerators.ENUMERATOR_VALUE.name: self.ENUMERATOR_VALUE

        }


"""
======================================== EVENTS RELATED TABLES ======================================== 
"""


class Events(BaseTableModel):
    """
    Class represents EVENTS TABLE.
    """
    __tablename__ = 'EVENTS'

    EVENT_ID = Column(String(100), primary_key=True)
    TYPE = Column(String(100), nullable=False)
    INPUT = Column(Text)
    OUTPUT = Column(Text)
    STARTED_AT = Column(DateTime, nullable=False)
    FINISHED_AT = Column(DateTime, nullable=False)
    CREATED_BY = Column(String(100), nullable=False)
    PROJECT_ID = Column(String(100))
    GROUP_ID = Column(String(100))
    IS_ACTIVE = Column(Boolean, nullable=False)
    STATUS = Column(String(100), nullable=False)
    STATUS_CODE = Column(Integer)

    def get_pk_values(self):
        return {
            Events.EVENT_ID.name: self.EVENT_ID
        }


class SubEvents(BaseTableModel):
    """
    Class represents SUB_EVENTS table.
    """
    __tablename__ = 'SUB_EVENTS'

    EVENT_ID = Column(String(100), primary_key=True)
    SEQUENCE_NUMBER = Column(Integer, primary_key=True)
    TYPE = Column(String(100))
    INPUT = Column(Text)
    OUTPUT = Column(Text)
    STARTED_AT = Column(DateTime, nullable=False)
    FINISHED_AT = Column(DateTime, nullable=False)
    IS_ACTIVE = Column(Boolean, nullable=False)
    STATUS = Column(String(100), nullable=False)

    def get_pk_values(self):
        return {
            SubEvents.EVENT_ID.name: self.EVENT_ID,
            SubEvents.SEQUENCE_NUMBER.name: self.SEQUENCE_NUMBER

        }
