from django.db import transaction, IntegrityError
from microblog_app.models import *
import random
import string
import timeit
from time import time

USER_COUNT = 500
MAX_POSTS_PER_USER = 100
MAX_FOLLOWS_PER_USER = 50
MAX_LIKES_PER_USER = 50
MAX_SHARES_PER_USER = 50
MAX_REPLIES_PER_USER = 50

def random_string():
	return ''.join(random.choice(string.ascii_uppercase) for x in range(3))

@transaction.commit_on_success
def load():
	start = time()
	total_users = 0
	total_posts = 0
	users = []
	print "creating models..."
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
		users.append(user)
		# create some posts
		post_count = random.randint(0, MAX_POSTS_PER_USER)
		user_posts = []
		for p in range(post_count):
			total_posts += 1
			post = Post(
				user=user, 
				text="Hey there, I'm post "+str(total_posts)+", I have some dummy text "
				+"here to simulate real life posts, how cool is that? I was posted by "
				+user.full_name()+" and these are random strings to make me searchable _"
				+random_string()+" _"+random_string())
			user_posts.append(post)
		Post.objects.bulk_create(user_posts)
		# follow some random users
		max_follows = min(MAX_FOLLOWS_PER_USER, total_users)
		follow_count = random.randint(0, max_follows)
		followees = random.sample(users,  max_follows)
		user_follows = []
		for followee in followees:
			if followee is not user:
				follow = Follow(follower=user, followee=followee)
				user_follows.append(follow)
		Follow.objects.bulk_create(user_follows)
		# share some random posts
		max_shares = min(MAX_SHARES_PER_USER, total_posts)
		share_count = random.randint(0, max_shares)		
		posts_to_share = Post.objects.all().order_by('?')[:share_count]
		user_shares = []
		for post in posts_to_share:
			share = Share(user=user, post=post)
			user_shares.append(share)
		Share.objects.bulk_create(user_shares)
		# like some random posts
		max_likes = min(MAX_LIKES_PER_USER, total_posts)
		like_count = random.randint(0, max_likes)
		posts_to_like = Post.objects.all().order_by('?')[:like_count]
		user_likes = []
		for post in posts_to_like:
			like = Like(user=user, post=post)
			user_likes.append(like)
		Like.objects.bulk_create(user_likes)
		# reply to some random posts
		max_replies = min(MAX_REPLIES_PER_USER, total_posts)
		reply_count = random.randint(0, max_replies)
		posts_to_reply = Post.objects.all().order_by('?')[:reply_count]
		user_replies = []
		for post in posts_to_reply:
			reply = Post(
				user=user, 
				in_reply_to=post,
				text="Look at me, I'm a reply to post #"+str(post.id)+", I have some dummy text "
				+"here to simulate real life posts, how cool is that? Well, it seems "
				+"like my creator has run out of ideas, so, see you tomorrow!")
			user_replies.append(reply)
		Post.objects.bulk_create(user_replies)
		print "created user %i" % u

	# swhow stats
	print 'users: '+str(User.objects.count())
	print 'follows: '+str(Follow.objects.count())
	print 'posts: '+str(Post.objects.count())
	print 'likes: '+str(Like.objects.count())
	print 'shares: '+str(Share.objects.count())
	elapsed = time() - start
	print 'completed in %f seconds' % elapsed
	

def timed_load():
	timeit.Timer("load()","from __main__ import load")

def main():
	load()

if __name__ == '__main__':
	main()
