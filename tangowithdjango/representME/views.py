from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout

from representME.models import Topic
from representME.forms import LawCommentForm
from helper import *

# For the reverse() functionality
from django.core.urlresolvers import reverse

from django.http import HttpResponseRedirect
from itertools import chain


def index(request):
    """
    :return: Sets the context for the not logged in OR logged in index page
    """

    # Try getting a user from database
    final_url = False
    try:
        # If user is logged in, we can get a user from DB
        msp_user = User.objects.get(username=request.user)
        # Get UserProfile from database
        msp_userprofile = UserProfile.objects.get(user=msp_user)
        # If user is MSP
        if msp_userprofile.msptype:
            # Set URL to which will be MSP user redirected (based on his first and last name
            final_url = msp_user.first_name.lower() + '-' + msp_user.last_name.lower()
    except:
        pass

    # If it's the MSP who's logged in, go to the MSP page instead of user page
    if final_url:
        return HttpResponseRedirect(reverse('msp', args=(final_url,)))

    # If it's the logged in user go to the logged in index and in context dictionary return data for
    # logged in index page
    elif request.user.is_authenticated():
        return render(request, 'representme/index-logged.html', get_index_page(request.user, True))

    # If the user is not logged in, just render basic index for not logged in user
    return render(request, 'representme/index.html', get_index_page(request.user, False))


def msp(request, msp_name):
    """
    :param msp_name: An msp name as a String firstname-surname
    :return: the context for the individual msp page
    """
    names = msp_name.split('-')
    context_dict = {}
    this_user_object = None
    try:
        #try to retrieve MSP with matching first and last name
        msp = MSP.objects.get(firstname__iexact=names[0], lastname__iexact=names[1])

        # Add MSP object to dictionary
        context_dict['msp'] = msp

        # default users
        context_dict['is_msp'] = False
        context_dict['is_this_msp'] = False
        context_dict['score'] = -1

        # If user is logged in, we want to check whether this MSP is one of his/her MSPs
        # therefore we need a dictionary of user msps
        user_msps = []
        if request.user.is_authenticated():
            this_user_object = request.user
            this_user = UserProfile.objects.get(user=this_user_object)
            this_user_names = User.objects.get(username=this_user_object)
            user_msps = get_msps(this_user.postcode)
            # check if this guy is an msp, and more specifically this msp
            if this_user.msptype:
                context_dict['is_msp'] = True
                if this_user_names.first_name == msp.firstname and this_user_names.last_name == msp.lastname:
                    context_dict['is_this_msp'] = True
                    context_dict['score'] = get_score(msp)

        # as a default, the MSP is not user's MSP:
        context_dict['is_my_msp'] = False
        # if it's not user's MSP, default for match is 0
        context_dict['match'] = 0

        # Go over the dictionary of user_msps and check whether one of the msps is equal to this msp
        if msp in user_msps and len(user_msps) > 0:
            context_dict['is_my_msp'] = True
            context_dict['match'] = computeMatch(this_user_object, msp)

        # get laws msp has voted on + excerpts
        context_dict['msp_laws'] = get_laws(request, msp)

        context_dict['msp_positions'] = get_positions(msp)

    except MSP.DoesNotExist:
        pass

    #not sure what to do if this happens!
    except MSP.MultipleObjectsReturned:
        pass

    return render(request, 'representme/msp.html', context_dict)


def law(request, law_name):
    """
    :param law_name: A law name
    :return: The context for the individual law page
    """
    context_dict = {}
    # In case user is not logged in, this is the default
    this_user_object = None

    # Try getting a law from database
    try:
        law = Law.objects.get(name=law_name)
        # Try getting all comments associated with the law
        comments = Comment.objects.order_by('-time').filter(law=law)
        # Get how many user votes are there for the law
        votes = UserVote.objects.filter(law=law)
        # Users voted for
        context_dict['votes_for'] = votes.filter(vote=True).count()
        # Users voted against
        context_dict['votes_against'] = votes.filter(vote=False).count()
        context_dict['law'] = law
        # Set whether a law is upcoming or past
        context_dict['upcoming'] = get_time_tag(law)
        # Create a comment form
        context_dict['commentForm'] = LawCommentForm()
        # Load up comments
        context_dict['comments'] = comments
        context_dict['comments_number'] = comments.count()

        # default MSP type
        context_dict['is_msp'] = False
        # Get user MSPs if user is logged in
        user_msps = []
        if request.user.is_authenticated():
            this_user_object = request.user
            this_user = UserProfile.objects.get(user=this_user_object)
            this_user_names = User.objects.get(username=this_user_object)
            user_msps = get_msps(this_user.postcode)
            if this_user.msptype:
                context_dict['is_msp'] = True
                context_dict['vote'] = get_vote_is_msp(this_user_names, law)

        user_msps_results = []
        # for each of those user_msps get the vote for this law and add the pair to the dictionary to be returned
        for msp in user_msps:
            try:
                msp_vote = MSPVote.objects.get(msp=msp, law=law)
            except MSPVote.DoesNotExist:
                msp_vote = ''
            user_msps_results.append([msp, msp_vote])

        # TODO: might get error in templates if db is not complete and an MSP vote is ''
        # delete this and the print once it is tested
        print user_msps_results

        context_dict['user_msps'] = user_msps_results

        # Get user vote if user voted
        context_dict['user_vote'] = ''
        try:
            context_dict['user_vote'] = UserVote.objects.get(user=this_user_object, law=law)
        except UserVote.DoesNotExist:
            pass
    except Law.DoesNotExist:
        pass

    return render(request, 'representme/law.html', context_dict)


def search(request):
    """
    :return: The context for the search page
    """
    if request.method == 'POST':
        query_string = request.POST.get('search')
        #split query terms on ' '
        query_terms = query_string.split()

        # create an empty lists to store search results
        search_results_topics = {}
        search_results_MSPs = []

        # retrieve fromt he database for time concerns (this will cache it)
        topics = Topic.objects.all()
        laws = Law.objects.all()
        msps = MSP.objects.all()

        #retrieve results for each query term
        for term in query_terms:
            for topic in topics.filter(name__icontains=term):
                search_results_topics[topic] = [[law, law.text[:300], get_time_tag(law)] for law in
                                                laws.filter(topic=topic)]
            for law in laws.filter(text__icontains=term):
                entry = [law, law.text[:300], get_time_tag(law)]
                if not law.topic in search_results_topics.keys():
                    search_results_topics[law.topic] = [entry]
                elif not entry in search_results_topics[law.topic]:
                    search_results_topics[law.topic].append(entry)
            for msp in chain(msps.filter(firstname__icontains=term), msps.filter(lastname__icontains=term)):
                if not msp in search_results_MSPs:
                    search_results_MSPs.append(msp)

        # if query is a postcode, but EXACTLY a postcode
        postcode_msps = get_msps(query_string)
        if len(postcode_msps) > 1:
            for msp in postcode_msps:
                if not msp in search_results_MSPs:
                    search_results_MSPs.append(msp)

        context_dict = {'search_results_topics': search_results_topics, 'search_results_MSPs': search_results_MSPs,
                        'query_string': query_string}

        return render(request, 'representme/search.html', context_dict)

    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render(request, 'representme/search.html', {})


def laws(request):
    """
    :return: the context for the laws page
    """
    context_dict = {}

    try:
        laws = Law.objects.order_by('-date')
        context_dict['laws'] = laws

    except:
        pass

    return render(request, 'representme/laws.html', context_dict)


def msps(request):
    """
    :return: The context for the msps page
    """
    context_dict = {}

    try:
        msps = MSP.objects.order_by('lastname')
        context_dict['msps'] = msps
    except MSP.DoesNotExist:
        pass
    return render(request, 'representme/msps.html', context_dict)


def user_login(request):
    """
    :return:
    """

    # Define a url where a user came from
    next_url = request.META.get('HTTP_REFERER')

    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        # We use request.POST.get('<variable>') as opposed to request.POST['<variable>'],
        # because the request.POST.get('<variable>') returns None, if the value does not exist,
        # while the request.POST['<variable>'] will raise key error exception
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user to the page where user came from.
                login(request, user)
                return HttpResponseRedirect(next_url)
            else:
                # An inactive account was used - no logging in!
                return HttpResponseRedirect(next_url + '#login-disabled')
        else:
            # Bad login details were provided. So we can't log the user in.
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponseRedirect(next_url + '#login-invalid')

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        return HttpResponseRedirect(next_url + '#login')


# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect(reverse('index'))


def register(request):
    userFormErrors = False
    userProfileFormErrors = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Set variable that will hold the password that is not encrypted
            # If we use user.password var after set password, it shows only encrypted one
            password = user.password

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Now we save the UserProfile model instance.
            profile.save()

            new_user = authenticate(username=user.username, password=password)

            login(request, new_user)

            # Go to the login page
            return HttpResponseRedirect(reverse('index'))

        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            userFormErrors = user_form.errors
            userProfileFormErrors = profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        return HttpResponseRedirect(reverse('index'))

    # Render the template depending on the context.
    return render(request,
                  'representme/index.html',
                  {'user_form': user_form, 'profile_form': profile_form, 'userFormErrors': userFormErrors,
                   'userProfileFormErrors': userProfileFormErrors, 'is_index': True})


@login_required
def user_vote(request):
    """
    :return: Adds user vote to the database and updates page
    """
    law_id = None
    vote = None

    # If the request method is get, set law_id and vote
    if request.method == 'GET':
        law_id = request.GET['law_id']
        vote = request.GET['vote']

    # Convert vote to proper boolean
    if vote == 'true':
        vote = True
    else:
        vote = False

    # Get law object from database
    law = Law.objects.get(id=int(law_id))

    # If something goes bad, we don't wanna update the HTML
    success = False

    # If law_id was set up correctly
    if law_id:
        # Get the user vote if exists
        user_law_vote = UserVote.objects.filter(user=request.user, law=law)
        # If it exists
        if user_law_vote:
            # Set vote for whatever user voted
            user_law_vote.voted_for = vote
            # Save the model
            user_law_vote.save()
            # We were successful this time!
            success = True
        # Otherwise create a new vote
        else:
            try:
                query = UserVote(user=request.user, law=law, vote=vote)
                query.save()
                # Again success!
                success = True
            except:
                pass

    # Return whether we were successful or not
    return HttpResponse(success)

@login_required
def add_comment(request):
    """
    :return: Adds comment to the database and updates page
    """
    law_id = None
    text = None
    comment_id = False
    law = None

    # If the request method is get, set law_id and vote
    if request.method == 'GET':
        law_id = request.GET['law_id']
        text = request.GET['text']
        if request.GET['comment_id'] != "":
            comment_id = request.GET['comment_id']

    try:
        # Get law object from database
        law = Law.objects.get(id=int(law_id))
    except:
        return HttpResponse(False)

    # If something goes bad, we don't wanna update the HTML
    output = False

    # If law_id was set up correctly then we can suppose
    # that text was set up correct as well
    if law_id:
        try:
            # If comment_id is not false, we're editing
            if comment_id:
                # We're searching for a combination of ID and a user, which will ensure that even if
                # a user passed the ID of the comment that he's not allowed to edit, the comment
                # will not be edited
                query = Comment.objects.get(id=int(comment_id), user=request.user)
                query.text = text
                query.save()

                # We don't need to return anything back, just a message saying it was successful
                return HttpResponse(True)

            # Otherwise creating a new comment
            else:
                # Save the comment to the database
                query = Comment(user=request.user, law=law, text=text)
                query.save()

                # Save a dictionary of data into output
                # Here we have date, id of the comment and username
                output = json.dumps({"date": query.time.strftime("%d/%m/%Y %H.%M"),
                                     "id": query.id,
                                     "username": request.user.username})
        except:
            pass

        # Return whether we were successful or not
        if output != False:
            # In case of success, return json
            return HttpResponse(output, content_type='application/json; charset=utf8')
        else:
            return HttpResponse(output)

def about(request):
    """
    :return: The context for the about page
    """


    return render(request, 'representme/about.html')