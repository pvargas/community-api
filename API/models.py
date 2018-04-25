import datetime

from peewee import *
from marshmallow_peewee import ModelSchema, Related
from playhouse.migrate import *

from passlib.hash import sha256_crypt
from passlib import pwd

from config import Database as config, App as app

from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, 
BadSignature, SignatureExpired)

DATABASE = MySQLDatabase(config.DB, host=config.HOST,
                         port=config.PORT, user=config.USER, password=config.PAS)
migrator = MySQLMigrator(DATABASE)

### models

class User(Model):
    id = PrimaryKeyField(primary_key=True)
    name = CharField(45, unique=True)
    member_since = DateTimeField(
        constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    is_moderator = BooleanField(constraints=[SQL('DEFAULT FALSE')])
    email = CharField(unique=True, default='')
    password = CharField(default='')

    class Meta:
        database = DATABASE
    
    @classmethod
    def create_user(cls, name, email, password, **kwargs):
        email = email.lower()        

        if (name == email) or (not name.isalnum()):            
            raise Exception("Invalid input")

        try:
            cls.select().where(
                (cls.email==email)|(cls.name**name)      
            ).get()
        except cls.DoesNotExist:
            user = cls(name=name, email=email)
            user.password = user.set_password(password)
            user.save()
            return user
        else:
            raise Exception("Username or email already exist.")


    @staticmethod
    def verify_auth_token(token):
        #serializer = Serializer(app.SECRET)
        serializer = Serializer(pwd.genword(entropy=56, charset="ascii_72", length=59))
        
        try:
            data = serializer.loads(token)
        except(SignatureExpired, BadSignature):
            return None
        else:
            user = User.get(User.id==data['id'])
            return user

    @staticmethod
    def set_password(password):       
        return sha256_crypt.encrypt(password)

    def verify_password(self, password):
        return sha256_crypt.verify(password, self.password)
    
    def generate_auth_token(self, expires=3600*12):
        #serializer = Serializer(app.SECRET, expires_in=expires)
        serializer = Serializer(pwd.genword(entropy=56, charset="ascii_72", length=59), expires_in=expires)
        
        return serializer.dumps({'id':self.id})

class Post(Model):
    id = PrimaryKeyField(primary_key=True)
    author = ForeignKeyField(User, backref='posts')
    title = CharField(300)
    is_url = BooleanField(constraints=[SQL('DEFAULT FALSE')])
    content = TextField()
    created_at = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    last_modified = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')])

    class Meta:
        database = DATABASE


class PostVotes(Model):
    post_id = ForeignKeyField(Post)
    user_id = ForeignKeyField(User)
    value = SmallIntegerField()

    class Meta:
        database = DATABASE
        primary_key = CompositeKey('post_id', 'user_id')


class Tag(Model):
    id = PrimaryKeyField(primary_key=True)
    name = CharField(45, unique=True)

    @classmethod
    def create_tag(cls, name, **kwargs):
        name = name.lower()
        try:
            cls.select().where(cls.name==name).get()
        except cls.DoesNotExist:
            tag = cls(name=name)
            tag.save()
            return tag
        else:
            raise Exception("tag already exist.")


    class Meta:
        database = DATABASE


class PostTags(Model):
    post_id = ForeignKeyField(Post)
    tag_id = ForeignKeyField(Tag)

    @classmethod
    def create_relationship(cls, post_id, tag_id):
        try:
            print("models.py log 1")
            cls.select().where(
                (cls.post_id==post_id)&(cls.tag_id==tag_id)
                ).get()
            print("models.py log 1.5")
        except cls.DoesNotExist:
            print("models.py log 2")
            relationship = cls(post_id=post_id, tag_id=tag_id)
            print("models.py log 3")
            relationship.save()
            print("models.py log 4")
            return relationship
        else:
            raise Exception("post-tag relationship already exists.")

    class Meta:
        database = DATABASE
        primary_key = CompositeKey('post_id', 'tag_id')


class Comment(Model):
    id = PrimaryKeyField(primary_key=True)
    #parent = ForeignKeyField('self', related_name='children', backref='comments', null=True )

    parent = IntegerField(null=True)

    author = ForeignKeyField(User, backref='posts')
    post = ForeignKeyField(Post, backref='comments')
    content = TextField()
    created_at = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    last_modified = DateTimeField(
        constraints=[SQL('DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')])

    class Meta:
        database = DATABASE


class CommentVotes(Model):
    comment_id = ForeignKeyField(Comment)
    user_id = ForeignKeyField(User)
    value = SmallIntegerField()

    class Meta:
        database = DATABASE
        primary_key = CompositeKey('comment_id', 'user_id')


### Schemas for all the above models


class UserSchema(ModelSchema):

    class Meta:
        model = User

class PostSchema(ModelSchema):

    author = Related()

    class Meta:
        model = Post


class PostVotesSchema(ModelSchema):

    class Meta:
        model = PostVotes


class TagSchema(ModelSchema):

    class Meta:
        model = Tag


class PostTagsSchema(ModelSchema):

    class Meta:
        model = PostTags


class CommentSchema(ModelSchema):
    #parent = Related()
    author = Related()
    #post = Related()

    class Meta:
        model = Comment


class CommentVotesSchema(ModelSchema):

    class Meta:
        model = CommentVotes


def initialize():
    DATABASE.connect()
    DATABASE.create_tables([User, Post, Tag, Comment, PostVotes,
                            CommentVotes, PostTags], safe=True)
    migrate(
        # Make `posts` allow NULL values.
        # migrator.drop_not_null('post', 'last_modified'),
        # migrator.drop_not_null('comment', 'last_modified')
        # migrator.add_column('user', 'email', User.email),
        # migrator.add_column('user', 'password', User.password),
    )
    DATABASE.close()
