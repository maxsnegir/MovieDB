import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Sum

User = get_user_model()


class MovieManager(models.Manager):

    def all_with_related_persons(self):
        qs = self.get_queryset()
        return qs.select_related('director').prefetch_related('writers',
                                                              'actors')

    def all_with_related_persons_and_scores(self):
        qs = self.all_with_related_persons()
        return qs.annotate(score=Sum('vote__value'))

    def top_movies(self, limit=10):
        qs = self.get_queryset()
        qs = qs.annotate(vote_sum=Sum('vote__value'))
        qs = qs.exclude(vote_sum=None)
        qs = qs.order_by('-vote_sum')[:limit]
        return qs


class Movie(models.Model):
    NOT_RATED = 0
    RATED_G = 1
    RATED_PG = 2
    RATED_R = 3
    RATINGS = (
        (NOT_RATED, 'NR - Not Rated'),
        (RATED_G, 'G - General Audience'),
        (RATED_PG, 'PG - Parental Guidance'),
        (RATED_R, 'R - Restricted'),
    )
    title = models.CharField(max_length=140)
    plot = models.TextField()
    year = models.PositiveIntegerField()
    rating = models.IntegerField(choices=RATINGS, default=NOT_RATED)
    runtime = models.PositiveIntegerField()
    website = models.URLField(blank=True)
    director = models.ForeignKey('Person', blank=True, null=True,
                                 related_name='directed',
                                 on_delete=models.SET_NULL)
    writers = models.ManyToManyField('Person', blank=True,
                                     related_name='writing_credits')
    actors = models.ManyToManyField(to='Person', through='Role',
                                    related_name='acting_credits',
                                    blank=True, )

    objects = MovieManager()

    class Meta:
        ordering = ('-year', 'title')

    def __str__(self):
        return f"{self.title}|{self.year}"


class PersonManager(models.Manager):
    def all_with_prefetch_movies(self):
        qs = self.get_queryset()
        return qs.prefetch_related('directed', 'writing_credits',
                                   'role_set__movie')


class Person(models.Model):
    first_name = models.CharField(max_length=140)
    last_name = models.CharField(max_length=140)
    born = models.DateField()
    died = models.DateField(blank=True, null=True)

    objects = PersonManager()

    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Role(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.DO_NOTHING)
    person = models.ForeignKey(Person, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=140)

    def __str__(self):
        return f"{self.movie.id} {self.person.id} {self.name}"

    class Meta:
        unique_together = ('movie', 'person', 'name')


class VoteManager(models.Manager):

    def get_vote_or_unsaved_blank_vote(self, movie, user):
        try:
            return Vote.objects.get(movie=movie, user=user)
        except Vote.DoesNotExist:
            return Vote(movie=movie, user=user)


class Vote(models.Model):
    UP = 1
    DOWN = -1

    VALUE_CHOICES = (
        (UP, '👍'),
        (DOWN, '👎')
    )

    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    voted_on = models.DateTimeField(auto_now=True)

    objects = VoteManager()

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user} {self.movie} {self.value}"


def movie_directory_path_with_uuid(instance, filename):
    return f"{instance.movie_id}/{uuid.uuid4()}"


class MovieImage(models.Model):
    image = models.ImageField(upload_to=movie_directory_path_with_uuid)
    uploaded = models.DateTimeField(auto_now_add=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
