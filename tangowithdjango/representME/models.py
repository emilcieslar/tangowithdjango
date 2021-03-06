from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Topic(models.Model):
    """
    represents topic for a law
    """
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(null=True)

    def __unicode__(self):
        return self.name


class Law(models.Model):
    CARRIED = 1
    DEFEATED = 2

    RESULTS = (
        (CARRIED, 'Carried'),
        (DEFEATED, 'Defeated')
    )

    name = models.CharField(max_length=15, unique=True)
    text = models.TextField()
    topic = models.ForeignKey(Topic)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    date = models.DateField(null=True)
    result = models.CharField(max_length=1, choices=RESULTS, null=True)

    def __unicode__(self):
        return self.name


class Party(models.Model):
    """
    represents party
    """
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField()
    colour = models.CharField(max_length=10, null=True)

    def __unicode__(self):
        return self.name


class Constituency(models.Model):
    """
    represents a constituency
    """
    parent = models.ForeignKey('self', default=0, null=True)
    name = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name

    def is_region(self):
        if self.parent is None:
            return True
        return False


class UserProfile(models.Model):
    # This line is required. Links UserProfile to a User model instance.
    user = models.OneToOneField(User)

    postcode = models.CharField(max_length=8)
    msptype = models.BooleanField(default=False)

    def __unicode__(self):
        return self.user.username


class UserVote(models.Model):
    """
    represents an msp's vote for a division
    """

    user = models.ForeignKey(User)
    law = models.ForeignKey(Law)
    vote = models.NullBooleanField()

    def __unicode__(self):
        return u'%s' % (self.vote)

    def is_true(self):
        if self.vote is True:
            return True
        return False

    def is_false(self):
        if self.vote is False:
            return True
        return False


class MSP(models.Model):
    """
    reprezents msps, stores presence, rebellions and status
    """

    foreignid = models.PositiveIntegerField(max_length=8, unique=True)
    constituency = models.ForeignKey(Constituency)
    party = models.ForeignKey(Party)
    firstname = models.CharField(max_length=128)
    lastname = models.CharField(max_length=128)
    presence = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    def __unicode__(self):
        return u'%s %s' % (self.firstname, self.lastname)


class Position(models.Model):
    """
    represents jobs that an msp can have
    """
    position_foreignid = models.PositiveIntegerField(max_length=8, unique=True)
    name = models.CharField(max_length=128)
    msp = models.ForeignKey(MSP)
    startdate = models.DateField()
    enddate = models.DateField()

    def __unicode__(self):
        return u'%s: %s - %s' % (self.name, self.startdate, self.enddate)


class MSPVote(models.Model):
    """
    represents an msp's vote for a division
    """
    YES = 1
    NO = 2
    ABSTAIN = 3
    ABSENT = 4
    VOTES = (
        (YES, 'Yes'),
        (NO, 'No'),
        (ABSTAIN, 'Abstain'),
        (ABSENT, 'Absent')
    )

    msp = models.ForeignKey(MSP)
    law = models.ForeignKey(Law)
    vote = models.CharField(max_length=1, choices=VOTES, null=True)

    def __unicode__(self):
        return self.vote


class Comment(models.Model):
    user = models.ForeignKey(User)
    law = models.ForeignKey(Law)
    time = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    def __unicode__(self):
        return self.text


