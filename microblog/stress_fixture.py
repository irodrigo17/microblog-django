from django.db import transaction, IntegrityError
from microblog_app.models import *
import random

USER_COUNT = 1000
MAX_POSTS_PER_USER = 500
MAX_FOLLOWS_PER_USER = 200
MAX_LIKES_PER_USER = 200
MAX_SHARES_PER_USER = 200
MAX_REPLIES_PER_USER = 200

@transaction.commit_on_success
def load():
	total_users = 0
	total_posts = 0
	for u in range(USER_COUNT):
		# create user
		total_users += 1
		user = User(
			username = 'user' + str(u), 
			first_name='First'+str(u), 
			last_name='Last'+str(u),
			email='user'+str(u)+'@email.com')
		user.set_password('pass')
		user.save()
		# create some posts
		post_count = random.randint(0, MAX_POSTS_PER_USER)
		for p in range(post_count):
			total_posts += 1
			post = Post(
				user=user, 
				text="Hey there, I'm post #"+str(total_posts)+", I have some dummy text "
				+"here to simulate real life posts, how cool is that? Well, it seems "
				+"like my creator has run out of ideas, so, see you tomorrow!")
			post.save()
		# follow some random users
		max_follows = min(MAX_FOLLOWS_PER_USER, total_users)
		follow_count = random.randint(0, max_follows)
		followees = random.sample(User.objects.all().exclude(username=user.username),  max_follows)
		for followee in followees:
			follow = Follow(follower=user, followee=followee)
			follow.save()
		# share some random posts
		max_shares = min(MAX_SHARES_PER_USER, total_posts)
		share_count = random.randint(0, max_shares)
		for s in range(share_count):
			post_id = random.randint(1, total_posts)
			post = Post.objects.get(pk=post_id)
			if post.user != user:
				share = Share(user=user, post=post)
				try:
					share.save()
				except IntegrityError:
					pass
		# like some random posts
		max_likes = min(MAX_LIKES_PER_USER, total_posts)
		like_count = random.randint(0, max_likes)
		for l in range(like_count):
			post_id = random.randint(1, total_posts)
			post = Post.objects.get(pk=post_id)
			like = Like(user=user, post=post)
			try:
				like.save()
			except IntegrityError:
				pass
		# reply to some random posts
		for r in range(MAX_REPLIES_PER_USER):
			post_id = random.randint(1, total_posts)
			post = Post.objects.get(pk=post_id)
			reply = Post(
				user=user, 
				in_reply_to=post,
				text="Look at me, I'm a reply to post #"+str(post.id)+", I have some dummy text "
				+"here to simulate real life posts, how cool is that? Well, it seems "
				+"like my creator has run out of ideas, so, see you tomorrow!")
			reply.save()
		# log results
		print 'created '+user.username

