import builtins
from datetime import datetime
from app import db


class PGResident(db.Model):
    __tablename__ = 'pg_residents'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    room_number = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # 'active', 'past'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    property = db.relationship('Property')
    user = db.relationship('User', back_populates='pg_residencies')

    __table_args__ = (
        db.UniqueConstraint('property_id', 'user_id', name='uq_property_resident'),
    )


class PGCommunityPost(db.Model):
    __tablename__ = 'pg_community_posts'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(30), default='general', nullable=False)  # 'general', 'announcement', 'question', 'maintenance', 'event'

    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    property = db.relationship('Property', back_populates='community_posts')
    author = db.relationship('User')
    comments = db.relationship('PGCommunityComment', back_populates='post', cascade='all, delete-orphan', order_by='PGCommunityComment.created_at.asc()')
    reports = db.relationship('PGCommunityReport', back_populates='post', cascade='all, delete-orphan')

    @builtins.property
    def author_is_owner(self):
        return bool(self.property and self.author and self.property.owner_id == self.author.id)

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'author_id': self.user_id,
            'author_name': self.author.name if self.author else 'Resident',
            'author_is_owner': self.author_is_owner,
            'title': self.title,
            'content': self.content,
            'post_type': self.post_type,
            'is_pinned': self.is_pinned,
            'comment_count': len([c for c in self.comments if not c.is_deleted]),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PGCommunityComment(db.Model):
    __tablename__ = 'pg_community_comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('pg_community_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    post = db.relationship('PGCommunityPost', back_populates='comments')
    author = db.relationship('User')

    @builtins.property
    def author_is_owner(self):
        return bool(self.post and self.post.property and self.author and self.post.property.owner_id == self.author.id)


class PGCommunityReport(db.Model):
    __tablename__ = 'pg_community_reports'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('pg_community_posts.id', ondelete='CASCADE'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = db.Column(db.String(150), nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='pending', nullable=False)  # 'pending', 'resolved', 'dismissed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    post = db.relationship('PGCommunityPost', back_populates='reports')
    reporter = db.relationship('User')
