"""Add pgvector extension and RAG tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimensions for text-embedding-3-large
EMBEDDING_DIMENSIONS = 3072


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create enum types for RAG
    knowledge_source_type = postgresql.ENUM(
        'curated', 'pubmed', 'medlineplus',
        name='knowledgesourcetype',
        create_type=False
    )
    knowledge_source_type.create(op.get_bind(), checkfirst=True)
    
    entity_type = postgresql.ENUM(
        'anomaly', 'correlation', 'insight', 'chat_message',
        name='historyentitytype',
        create_type=False
    )
    entity_type.create(op.get_bind(), checkfirst=True)
    
    message_role = postgresql.ENUM(
        'user', 'assistant', 'system',
        name='messagerole',
        create_type=False
    )
    message_role.create(op.get_bind(), checkfirst=True)

    # Create knowledge_embeddings table
    op.create_table(
        'knowledge_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column('source_type', knowledge_source_type, nullable=False),
        sa.Column('source_id', sa.String(500), nullable=True),  # e.g., PMID, file path
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=True),  # For chunked documents
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create HNSW index for fast similarity search on knowledge embeddings
    op.execute('''
        CREATE INDEX ix_knowledge_embeddings_vector 
        ON knowledge_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    ''')
    
    # Create indexes for filtering
    op.create_index('ix_knowledge_embeddings_source_type', 'knowledge_embeddings', ['source_type'])
    op.create_index('ix_knowledge_embeddings_source_id', 'knowledge_embeddings', ['source_id'])

    # Create user_history_embeddings table
    op.create_table(
        'user_history_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column('entity_type', entity_type, nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),  # Reference to original entity
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create HNSW index for user history embeddings
    op.execute('''
        CREATE INDEX ix_user_history_embeddings_vector 
        ON user_history_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    ''')
    
    # Create indexes for filtering by user
    op.create_index('ix_user_history_embeddings_user_entity', 'user_history_embeddings', 
                    ['user_id', 'entity_type'])

    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create index for active sessions
    op.create_index('ix_chat_sessions_user_active', 'chat_sessions', 
                    ['user_id', 'is_active', 'updated_at'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('role', message_role, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context_used', postgresql.JSONB(), nullable=True),  # Store retrieved context
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create index for message ordering
    op.create_index('ix_chat_messages_session_created', 'chat_messages', 
                    ['session_id', 'created_at'])


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index('ix_chat_messages_session_created')
    op.drop_table('chat_messages')
    
    op.drop_index('ix_chat_sessions_user_active')
    op.drop_table('chat_sessions')
    
    op.drop_index('ix_user_history_embeddings_user_entity')
    op.execute('DROP INDEX IF EXISTS ix_user_history_embeddings_vector')
    op.drop_table('user_history_embeddings')
    
    op.drop_index('ix_knowledge_embeddings_source_id')
    op.drop_index('ix_knowledge_embeddings_source_type')
    op.execute('DROP INDEX IF EXISTS ix_knowledge_embeddings_vector')
    op.drop_table('knowledge_embeddings')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS messagerole')
    op.execute('DROP TYPE IF EXISTS historyentitytype')
    op.execute('DROP TYPE IF EXISTS knowledgesourcetype')
    
    # Drop pgvector extension
    op.execute('DROP EXTENSION IF EXISTS vector')
