"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-14 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("conversation_summary", sa.Text(), nullable=True),
        sa.Column("conversation_json", sa.JSON(), nullable=False),
        sa.Column("source_platform", sa.String(length=50), nullable=True),
        sa.Column("source_model", sa.String(length=100), nullable=True),
        sa.Column("remix_of", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("likes_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("comments_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("remix_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("post_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "likes",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("post_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("post_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("posts_created_at_idx", "posts", [sa.text("created_at DESC")])
    op.create_index("messages_post_position_idx", "messages", ["post_id", "position"])
    op.create_index("likes_post_user_idx", "likes", ["post_id", "user_id"])
    op.create_index("posts_created_by_idx", "posts", ["created_by"])


def downgrade() -> None:
    op.drop_index("posts_created_by_idx", table_name="posts")
    op.drop_index("likes_post_user_idx", table_name="likes")
    op.drop_index("messages_post_position_idx", table_name="messages")
    op.drop_index("posts_created_at_idx", table_name="posts")

    op.drop_table("comments")
    op.drop_table("likes")
    op.drop_table("messages")
    op.drop_table("posts")
    op.drop_table("users")
