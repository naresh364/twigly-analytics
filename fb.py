import facebook

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    TIMESTAMP
    )
import tornado.web
from datetime import datetime

facebook_app_id = "***REMOVED***"
facebook_app_secret = "***REMOVED***"

fbBase = declarative_base()
fbengine_url = 'mysql+pymysql://root:***REMOVED***@localhost/fb?charset=utf8'

class fb_user(fbBase):
    __tablename__ = "fb_users"
    id = Column('id', String, primary_key=True)
    name = Column("name", String)
    profile_url = Column("profile_url", String)
    email = Column("email", String)
    access_token = Column("access_token", String)
    birthday = Column("birthday", Date)
    updated = Column("updated", TIMESTAMP)

class FBBaseHandler(tornado.web.RequestHandler):
    """Implements authentication via the Facebook JavaScript SDK cookie."""
    def get_current_user(self):
        cookies = dict((n, self.cookies[n].value) for n in self.cookies.keys())
        cookie = facebook.get_user_from_cookie(
            cookies, facebook_app_id, facebook_app_secret)
        if not cookie:
            return None

        fbengine = sqlalchemy.create_engine(fbengine_url)
        fbsession = scoped_session(sessionmaker(bind=fbengine))
        user = fbsession.query(fb_user).filter(fb_user.id == cookie["uid"]).one()
        if not user:
            # TODO: Make this fetch async rather than blocking
            graph = facebook.GraphAPI(cookie["access_token"])
            profile = graph.get_object("me?fields=email,link,birthday,name")
            newUser = fb_user()
            newUser.id = profile["id"]
            newUser.name = profile["name"]
            newUser.profile_url = profile["link"]
            newUser.access_token = cookie["access_token"]
            newUser.email = profile["email"]
            newUser.birthday = datetime.strptime(profile["birthday"], "%m/%d/%Y").date()
            fbsession.add(newUser)
            fbsession.commit()
        elif user.access_token != cookie["access_token"]:
            user.access_token = cookie["access_token"]
            fbsession.commit()
        
        fbsession.remove()
        return user

class VanvaasHandler(FBBaseHandler):
    def get(self):
        thisuser = self.get_current_user()
        print (thisuser)
        reactionsresult = {}
        commentsresult = {}
        if thisuser:
            graph = facebook.GraphAPI(access_token=thisuser.access_token, version="2.8")
            posts = graph.get_object("me/posts?fields=object_id,message,story,comments.limit(999),reactions.limit(999)&limit=20me/posts?fields=object_id,message,story,comments.limit(999),reactions.limit(999)&limit=20")
            print (posts)
            reactions = {}
            comments = {}
            lookup = {}
            if posts:
                for post in posts["data"]:
                    if "reactions" in post:
                        for reaction in post["reactions"]["data"]:
                            lookup[reaction["id"]] = reaction["name"]
                            if reaction["id"] in reactions:
                                reactions[reaction["id"]] += 1
                            else:
                                reactions[reaction["id"]] = 1
                    if "comments" in post:
                        for comment in post["comments"]["data"]:
                            lookup[comment["from"]["id"]] = comment["from"]["name"]
                            if comment["from"]["id"] in comments:
                                comments[comment["from"]["id"]] += 1
                            else:
                                comments[comment["from"]["id"]] = 1

            reactionslist = sorted([{"id": x, "count": reactions[x], "name": lookup[x]} for x in reactions], key=lambda x: -x["count"])
            reactionsresult = reactionslist[0]

            commentslist = sorted([{"id": x, "count": comments[x], "name": lookup[x]} for x in comments], key=lambda x: -x["count"])[0]
            commentsresult = commentslist[0]
            if reactionsresult["id"] == commentsresult["id"]:
                if len(commentslist) > 1:
                    commentsresult = commentslist[1]
                else:
                    commentsresult = {}

        self.render("templates/fbexample.html", facebook_app_id=facebook_app_id, reactionsresult=reactionsresult, commentsresult=commentsresult)